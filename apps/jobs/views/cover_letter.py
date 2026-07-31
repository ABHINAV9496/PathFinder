import logging
import re

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from apps.jobs.llm_client import generate_with_llm
from apps.jobs.models import AIConfig, Application, Job
from apps.jobs.profile_manager import load_profile
from apps.jobs.views.base import BaseAPIView
from apps.jobs.views.generate_cv import _extract_resume_text

logger = logging.getLogger(__name__)

# =============================================================================
# Anchored Summary — cover_letter.py
# =============================================================================
# PURPOSE: Generates AI cover letters via LLM (OpenAI-compatible providers).
# Invoked by POST /api/jobs/<id>/cover-letter.
#
# KEY COMPONENTS:
#   _build_system_prompt() — returns the system prompt for the LLM, containing:
#     - OUTPUT RULES: no labels, no thinking tags, must start with salutation
#     - STRUCTURE: 4-5 paragraphs, mandatory "Dear Hiring Manager," first line,
#       opening references JD detail, body connects relevant projects, closing
#       varies and references a JD-specific point not mentioned earlier
#     - BANNED: forbidden phrases, passive openers, generic closings
#     - NO REPETITION: no repeating JD phrases across paragraphs
#     - ACRONYM RULES: never expand/define acronyms (esp. RAG)
#     - SKILL GAP RULE: forbidden to mention missing skills
#     - NUMERIC CLAIM RULE: every number must exist verbatim in source data
#     - GROUNDED CLAIM RULE: soft claims banned unless backed by specific tools
#     - JD TECHNOLOGY LIST RULE: don't claim full tech groups; verify individually
#     - TONE: human-like, no AI tells, no corporate fluff
#     - SENTENCE STRUCTURE RULE: max 2 comma clauses before main verb
#     - PROJECT ATTRIBUTION RULE: tech must belong to the project it's tied to
#     - LOCATION / AVAILABILITY / SENIORITY AWARENESS rules
#     - FINAL CHECK: spelling, tech names, salutation present, signature intact
#   _build_user_prompt(job) — injects JD details, candidate profile, skill gaps
#   _validate_letter(letter, job) — deterministic post-generation checks:
#     a. Salutation presence   b. Signature stripping/reappending
#     c. Forbidden skills      d. Project attribution
#     e. Numeric claims        f. Ungrounded claims
#     g. Placeholder URL replacement
#   GenerateCoverLetter.post() — orchestrates generation, validation, optional
#     retry on hard issues, and saves to Application model.
#
# KEY VARIABLES / DATA:
#   _PROFILE_CACHE — lazy-loaded candidate profile from profile_manager
#   _ACRONYM_MAP — bidirectional acronym↔expansion lookup
#   _SEMANTIC_CLUSTERS — tech clusters for project-attribution broadening
#   _UNGROUNDED_CLAIM_PATTERNS — maps vague categories → grounding keywords
#   _COVERAGE_KEYWORDS — maps requirement categories → JD/letter keywords
#   _PLACEHOLDER_DOMAINS — URLs to replace with real profile URLs
# =============================================================================

_PROFILE_CACHE = None

def _get_profile():
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        _PROFILE_CACHE = load_profile()
    return _PROFILE_CACHE


def _clean_cover_letter(text: str) -> str:
    text = re.sub(r"\s*--\s*", ", ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _build_signature() -> str:
    name = _get_profile().get("name", "Developer")
    phone = _get_profile().get("phone", "")
    portfolio = _get_profile().get("portfolio", "")
    github = _get_profile().get("github", "")
    linkedin = _get_profile().get("linkedin", "")

    lines = [name]
    if phone:
        lines.append(phone)
    if portfolio:
        lines.append(f"Portfolio: {portfolio}")
    if github:
        lines.append(f"GitHub: {github}")
    if linkedin:
        lines.append(f"LinkedIn: {linkedin}")
    return "Regards,\n" + "\n".join(lines)


def _compute_skill_gap(job) -> tuple[str, str]:
    """Compare job requirements against candidate profile.
    Returns (candidate_has, candidate_missing) as comma-separated strings."""
    candidate_skills_lower = set()
    for cat_skills in _get_profile().get("skills", {}).values():
        for s in cat_skills:
            candidate_skills_lower.add(s.lower())

    has_set = set()
    for s in (job.matched_skills or []):
        has_set.add(s)

    missing_set = set()
    for s in (job.skill_gaps or []):
        missing_set.add(s)

    desc = (job.description or "").lower()
    extra_keywords = {
        "rust", "go", "golang", "java", "scala", "ruby", "php", "c++",
        "graphql", "grpc", "mongodb", "cassandra", "neo4j", "elasticsearch",
        "kubernetes", "k8s", "terraform", "gcp", "azure", "flutter",
        "swift", "kotlin", "selenium", "cypress", "playwright",
        "kafka", "rabbitmq", "airflow", "spark", "hadoop",
        "tableau", "power bi", "blockchain", "web3",
    }
    for kw in extra_keywords:
        if re.search(rf"\b{re.escape(kw)}\b", desc) and kw not in candidate_skills_lower:
            display = kw.upper() if kw in ("go", "golang", "c++") else kw.title()
            if kw == "k8s":
                display = "Kubernetes"
            missing_set.add(display)

    has_lower = {s.lower() for s in has_set}
    missing_set = {s for s in missing_set if s.lower() not in has_lower}

    has_list = sorted(has_set, key=str.lower)
    missing_list = sorted(missing_set, key=str.lower)

    has_text = ", ".join(has_list) if has_list else "None"
    missing_text = ", ".join(missing_list) if missing_list else "None -- candidate matches all listed requirements"

    return has_text, missing_text


def _build_system_prompt() -> str:
    signature = _build_signature()

    return f"""You are a professional cover letter writer for a software developer.

OUTPUT RULES:
- Output ONLY the cover letter. No labels, no analysis, no commentary.
- NEVER output <think> or <thinking> or <thought> tags. Just the letter itself.
- The letter must always begin with the line "Dear Hiring Manager," -- never omit this, even when varying the rest of the opening.
- NEVER use "I am writing to express my interest" or "I am excited to apply".
- NEVER use emojis, markdown formatting, bold, bullet points, or dashes (--) around descriptions.
- Plain text only, ATS-friendly.

STRUCTURE (4-5 short paragraphs, under 180 words body):
1. SALUTATION (mandatory, always first): The very first line of the letter must be exactly "Dear Hiring Manager," on its own line, followed by a blank line. This line is never optional and is never varied, skipped, or merged into the next sentence. Only the sentence that comes AFTER the salutation should vary and reference a specific JD detail -- the salutation itself stays fixed every time.
2. Opening paragraph (comes after the salutation line): Reference something SPECIFIC from the job description -- a named technology they use, the domain they operate in, or a problem they describe. Do NOT open with "I am applying for the {{title}} position at {{company}}" every time. Vary your opening sentence.
3. Body: Connect your most relevant project(s) and skills to what this specific job needs. Choose which project(s) to highlight based on relevance to THIS job, not a fixed order.
4. If the JD mentions Docker, AWS, CI/CD, Kubernetes, or DevOps -- naturally weave in relevant DevOps experience. If it mentions AI/ML/LLM -- naturally weave in relevant AI experience. Only mention what is relevant.
5. Closing: A brief, confident close. Vary it between letters -- do NOT always use the same closing sentence.

Then append the signature block exactly as given in the SIGNATURE section below, on a new line after the closing paragraph.

BANNED:
- "I am genuinely interested in contributing to X and happy to discuss how I can add value from day one" -- never use this closer.
- "I am writing to express my interest in the X position" -- never use this opener.
- "Dear Hiring Manager at {{company}}" -- always use exactly "Dear Hiring Manager," and let the company name appear naturally within the first paragraph.
- Any sentence that could apply to literally any job without changes.
- Opening with "I am writing to express my interest in the X position at Y" or "I came across the X position and wanted to apply" -- vary the opening sentence, make it specific to a JD detail.
- Passive or indirect openers like "As I read about X, I am reminded of..." or "I was impressed by...". Open with a direct, confident statement connecting a specific JD detail to a specific thing you have built or done -- active voice, no throat-clearing.
- Stacking more than one soft/eager phrase in the same letter. Phrases like "I believe my experience aligns with," "I am confident that," "I am excited to bring," and "I would be a strong fit" are each acceptable ONCE per letter, never twice, never back-to-back in adjacent sentences. Pick the single strongest one and cut the rest -- replace with a concrete statement (a result, a number, a specific technology used).
- Generic closing lines like "I look forward to discussing my qualifications further" or "I look forward to discussing how I can contribute." The closing sentence must reference one specific responsibility, technology, or goal from the JD that has NOT been mentioned earlier in the letter, framed as what you are looking forward to working on.

NO REPETITION:
- Do not repeat any phrase, sentence fragment, or distinctive wording from the job description more than once in the entire letter. If you reference a JD detail (a technology, a responsibility, a stated need) in one paragraph, do not paraphrase or restate that same detail again later -- move on to a new point instead.
- Before finalizing, mentally check: does any sentence in paragraph 2 or later restate an idea already covered in paragraph 1? If so, cut it or replace it with a new point.
- The closing paragraph must reference something specific and different from what was already said -- not a generic restatement like "I am looking forward to discussing how my expertise can benefit {{company}}." Tie it to a concrete next step or a specific value point not yet mentioned.

ACRONYM RULES:
- Never expand, define, or explain an acronym or technical term unless the exact expansion is explicitly given in the job description or candidate profile provided to you.
- If a term appears only as an acronym (e.g. RAG, LLM, CI/CD, DRF, RBAC), use it as-is without spelling out what it stands for.
- Do not guess expansions. Incorrect expansions (e.g. inventing a wrong full form for an acronym) are worse than using the acronym alone.
- This applies especially to RAG -- RAG must NEVER be expanded or defined in your output under any circumstances, even if you believe you know what it stands for. Write 'RAG' alone, exactly as given, with no parenthetical expansion, ever. Do NOT write "Retrieval-Augmented Generation", "Real-time Agents", "Rhetorical Argument Generation", or any other expansion. Just RAG.

SKILL GAP RULE -- MANDATORY, NON-NEGOTIABLE:
You are given two lists: SKILLS THE CANDIDATE HAS THAT MATCH THIS JOB, and SKILLS THIS JOB REQUIRES THAT THE CANDIDATE DOES NOT HAVE.
- You may ONLY write about skills from the first list as things the candidate has, uses, or has experience with.
- Every skill name in the second list is FORBIDDEN to appear anywhere in your output, in any form -- not as something the candidate has, not as something that 'aligns with' their experience, not quoted from the job description, not implied, not mentioned as a learning goal. Treat each name in that list as a word you are not allowed to write.
- Before you finalize your response, re-read it and check: does any sentence contain a word from the missing-skills list? If yes, rewrite that sentence to remove it entirely and replace it with a point about a skill from the has-list instead.
- Do not summarize or paraphrase the job's full requirement line (e.g. 'backend services in X, Y, and Z') if it contains any missing skill -- instead reference only the specific matching skills from that same line, worded as your own list, not the job's list.
- This rule overrides any instinct to sound comprehensive or to mirror the job description's phrasing. Precision about actual skills matters more than matching every word of the JD.

NUMERIC CLAIM RULE -- MANDATORY, NON-NEGOTIABLE:
- Every number, percentage, statistic, or measurable claim in your output (e.g. '40%', 'sub-100ms', '500K+ LOC', '99%+ completion', '35 percent') must appear VERBATIM in the PROJECTS or EXPERIENCE data given to you below, attached to the exact same achievement it describes there.
- You are FORBIDDEN from moving a number from one achievement to a different achievement, combining two numbers, rounding a number, or inventing a new number that doesn't appear in the source data at all.
- If you want to mention an achievement that has a number attached in the source data, you must keep the number attached to the SAME technology/action it was originally paired with. Do not detach '40 percent' from 'reduced initial page load' and reattach it to 'deployment time' or any other claim.
- If no specific number supports the point you want to make, make the point WITHOUT a number rather than inventing one. A qualitative claim with no number is always safer and more honest than a fabricated statistic.
- Before finalizing, check every number in your draft against the source data: can you point to the exact sentence in PROJECTS/EXPERIENCE it came from, attached to the same claim? If not, delete it or rewrite without it.

GROUNDED CLAIM RULE -- MANDATORY:
- Every claim about a skill, practice, or capability (e.g. testing, monitoring, code review, CI/CD, security practices) must be backed by something specific in the candidate's PROJECTS or EXPERIENCE data below -- not just a general category match.
- Do NOT write soft, unverifiable claims like 'I'm comfortable with testing' or 'I have experience with the full lifecycle including testing' unless the source data actually names a specific testing tool, framework, or practice (e.g. pytest, Jest, CI test suite, integration tests). A vague gesture at a skill with no supporting detail is a red flag to reviewers -- it reads as filling a checklist rather than describing real experience.
- If the job requires a skill (e.g. testing) that has no specific, nameable backing in the candidate's data, do NOT mention that skill at all, vague or otherwise. Silence on an unaddressed requirement is more credible than a soft, unsupported claim about it. It is better to leave a gap unaddressed than to paper over it with vague language.
- This applies to any skill category, not just testing: monitoring, security, accessibility, compliance, etc. -- same rule.

JD TECHNOLOGY LIST RULE:
- When the job description lists multiple technologies together (e.g. 'REST, webhooks, and OAuth' or 'Go, Java, Python, or C++'), you may NEVER claim the full list as something you have experience with as a group.
- Check each individual item in that list separately against the candidate's actual PROJECTS and EXPERIENCE data. Only mention the specific items that are individually present in the source data. Drop the rest silently -- do not round up to 'familiar territory' or 'exposure to' for items not explicitly in the source data.
- Never claim a skill 'from both projects' or 'from my experience' as a blanket statement without verifying it's true for EACH project or experience entry you're attributing it to. If OAuth is true for Project A but not Project B, say so specifically tied to Project A only -- do not generalize it across both.

TONE -- WRITE LIKE A HUMAN, NOT AN AI:
- Write the way a sharp engineer would actually write to a hiring manager they respect -- direct, specific, a little informal in rhythm, not corporate-polished.
- Vary sentence length deliberately. Follow a longer sentence with a short one. Avoid three sentences in a row with the same length and structure -- that rhythm is a known AI tell.
- Do not use inflated adjectives that add no information: 'passionate', 'thrilled', 'excited to leverage', 'robust', 'seamless', 'cutting-edge', 'dynamic', 'comprehensive'. If a sentence still makes sense with the adjective deleted, delete it.
- Do not use symmetric three-part lists for their own rhythm ('design, build, and ship' / 'fast, reliable, and scalable') unless all three words are doing distinct, necessary work -- these are a strong AI-writing tell when overused.
- Avoid corporate transition phrases: 'Furthermore', 'Moreover', 'In addition to this', 'It is worth noting that'. Just state the next point directly.
- Every sentence should contain either a specific technical detail, a real outcome, or a direct connection to something the job actually asks for. If a sentence could be deleted without losing any specific information, delete it.
- One instance of genuine personality or specific curiosity about the company/problem is good (e.g. naming a real detail from the JD that's interesting, not just matching keywords). Flattery without specifics ('I'm impressed by your innovative culture') is banned.

SENTENCE STRUCTURE RULE:
- Do not write sentences with more than two comma-separated clauses stacked before the main verb. If a sentence needs to list multiple things (e.g. 'event streaming, RAG pipelines, and multi-service coordination') AND make a claim about them (e.g. 'has accelerated my growth'), split it into two sentences: one that lists/describes the work, and a second, short one that makes the claim. Short sentences after a longer one are good rhythm -- long embedded-list sentences that bury the main verb are not.
- Read every sentence and check: can a reader identify the subject and main verb within the first 12-15 words? If not, restructure it.

PROJECT ATTRIBUTION RULE:
- Each project can only be described using the technologies and responsibilities listed for that specific project in the PROJECTS section of the prompt.
- Do not attribute a skill, technology, or responsibility to a project unless it is explicitly listed under that project's own entry.
- If a skill is only mentioned in the candidate's general skills list or under a different project or experience, either mention it generally without tying it to the wrong project, or attribute it to the correct project or role it actually belongs to.
- Never write "in Project X, I used Skill Y" if Skill Y does not appear in Project X's Tech line.

LOCATION RULE:
- Only make a claim about relocation, remote availability, or being 'based in' a location if the candidate's actual location and relocation preference are given to you explicitly below.
- Never state a firm commitment like 'I am ready to relocate to X' unless explicitly told the candidate is open to relocation. If relocation openness is not specified, either use soft, non-committal phrasing (e.g. 'happy to discuss location/relocation details') or omit location commentary entirely -- do not invent a decision on the candidate's behalf.
- Never name a specific city as a place the candidate is 'ready to relocate to' unless that is the job's actual stated location, given to you below, AND the candidate's relocation preference explicitly allows it.

AVAILABILITY RULE:
- Only make a claim about notice period, start date, or ability to join immediately if the candidate's actual availability is given to you explicitly below.
- Never state 'I am comfortable joining immediately' or 'I can start right away' or any similar claim unless the candidate's provided availability explicitly supports it.
- If availability is unspecified or indicates a notice period, either omit availability commentary entirely, or phrase it accurately and non-committally (e.g. 'happy to discuss timeline and availability further'). Do not round a notice period down to 'immediate' or invent urgency the candidate hasn't stated.

SENIORITY AWARENESS RULE:
- If the job title includes a seniority marker (Senior, Staff, Lead, Principal, etc.) and the candidate's total experience (given below) is under 3 years, do not write the letter as if seniority is a non-issue.
- In this case, spend one sentence making an honest, specific case for depth over tenure -- e.g. citing the scope or complexity of a real project (architecture decisions, scale numbers, ownership of a full system) rather than years. Do not apologize for experience level or draw attention to it as a weakness. Do not ignore it either -- make the strongest honest case that complexity of work compensates for fewer years, using only real details from the candidate's projects/experience data.
- If the candidate's experience level roughly matches or exceeds what the title implies, this rule does not apply -- write normally.

SIGNATURE (append exactly as-is after the closing paragraph):
{signature}

FINAL CHECK (do this silently before outputting):
- Re-read your full draft once for spelling and word-choice errors (e.g. 'rolloff' instead of 'rollout', or any other malformed word). Fix any you find.
- Confirm every technology name is spelled correctly and matches standard industry naming (e.g. 'PostgreSQL' not 'Postgre SQL', 'Kubernetes' not 'Kuberneters').
- Confirm the letter still satisfies every rule above (grounded claims, no repeated JD phrases, salutation present, signature intact, no fabricated numbers) before finalizing your output.
- Only output the final, corrected version -- never show your proofreading process."""


def _build_user_prompt(job) -> str:
    name = _get_profile().get("name", "Developer")
    location = _get_profile().get("location", "India")
    role = _get_profile().get("role", "Full Stack Developer")
    experience_years = _get_profile().get("experience_years", 1)

    experience = _get_profile().get("experience", [])
    exp_text = ""
    if experience:
        e = experience[0]
        exp_text = f"{e.get('role', role)} at {e.get('company', 'Unknown')}, {e.get('location', location)}"
        if e.get("duration"):
            exp_text += f" ({e['duration']})"

    desc = (job.description or "")[:3000]

    candidate_has, candidate_missing = _compute_skill_gap(job)

    projects_text = ""
    for p in _get_profile().get("projects", []):
        projects_text += (
            f"- {p['name']}: {p['description']} "
            f"(Tech: {', '.join(p['tech'][:8])})\n"
        )

    experience_text = ""
    for e in experience:
        experience_text += (
            f"- {e.get('role', role)} at {e.get('company', 'Unknown')}, "
            f"{e.get('location', location)}"
        )
        if e.get("duration"):
            experience_text += f" ({e['duration']})"
        experience_text += "\n"

    portfolio = _get_profile().get("portfolio", "")
    github = _get_profile().get("github", "")
    linkedin = _get_profile().get("linkedin", "")
    urls_text = []
    if portfolio:
        urls_text.append(f"Portfolio: {portfolio}")
    if github:
        urls_text.append(f"GitHub: {github}")
    if linkedin:
        urls_text.append(f"LinkedIn: {linkedin}")
    urls_block = "\n".join(urls_text) if urls_text else "None provided"

    return f"""Write a cover letter for this specific job application.

JOB:
Company: {job.company}
Title: {job.title}
Location: {job.location or 'Not specified'}

JOB DESCRIPTION:
{desc}

CANDIDATE:
Name: {name}
Role: {role}
Experience: {experience_years} year(s) -- {exp_text}
CANDIDATE TOTAL EXPERIENCE: {experience_years} year(s)
CANDIDATE LOCATION: {_get_profile().get('location', 'Not specified')}
OPEN TO RELOCATION: {_get_profile().get('open_to_relocation', 'Not specified')}
CANDIDATE AVAILABILITY: {_get_profile().get('availability', 'Not specified')}
Profile URLs:
{urls_block}

SKILLS THE CANDIDATE HAS THAT MATCH THIS JOB: {candidate_has}
SKILLS THIS JOB REQUIRES THAT THE CANDIDATE DOES NOT HAVE: {candidate_missing}

PROJECTS:
{projects_text}
EXPERIENCE:
{experience_text}
INSTRUCTIONS:
- You may ONLY write about skills from the has-list above. The missing-skills list is FORBIDDEN in your output.
- Identify 1-2 specific details from the job description above and reference at least one directly in your opening.
- Choose which project(s) to lead with based on relevance to THIS job's matched skills, not a fixed order.
- Keep it under 180 words in the body (excluding signature).
- Use the signature block provided in the system prompt exactly as-is.
- Do NOT add any text before or after the cover letter.
- When writing the signature, use the actual URLs from the Profile URLs section above -- do not invent or substitute placeholder URLs."""


_COVERAGE_KEYWORDS = {
    "test": ["test", "testing", "unit test", "integration test", "end-to-end", "e2e"],
    "ci/cd": ["ci/cd", "ci cd", "continuous integration", "continuous deployment", "pipeline"],
    "security": ["security", "compliance", "owasp", "vulnerability", "authentication"],
    "accessibility": ["accessibility", "a11y", "wcag", "screen reader"],
    "monitoring": ["monitoring", "observability", "logging", "alerting", "apm"],
    "documentation": ["documentation", "docs", "technical writing"],
    "agile": ["agile", "scrum", "sprint", "kanban"],
}


def _check_requirement_coverage(job, letter: str) -> list[str]:
    """Check if core JD requirements are addressed in the letter.
    Returns a list of warning strings (does not modify the letter)."""
    warnings = []
    desc = (job.description or "").lower()
    letter_lower = letter.lower()

    for category, keywords in _COVERAGE_KEYWORDS.items():
        jd_requires = False
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", desc):
                jd_requires = True
                break

        if not jd_requires:
            continue

        letter_addresses = False
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", letter_lower):
                letter_addresses = True
                break

        if not letter_addresses:
            warnings.append(
                f"JD requires '{category}' but letter does not address it"
            )

    return warnings


_AGGREGATE_REFERENCES = {
    "both projects", "both codebases", "both platforms", "each project",
    "these projects", "all my projects", "across both", "both applications",
    "across projects", "across all my", "in my work", "throughout my",
    "on multiple", "in various", "my experience with", "my work on",
}

_ACRONYM_MAP = {
    "drf": "django rest framework",
    "django rest framework": "drf",
    "llm": "large language model",
    "large language model": "llm",
    "rag": "retrieval augmented generation",
    "retrieval augmented generation": "rag",
    "ci/cd": "continuous integration continuous deployment",
    "continuous integration continuous deployment": "ci/cd",
    "ci cd": "continuous integration continuous deployment",
    "rbac": "role based access control",
    "role based access control": "rbac",
    "api": "application programming interface",
    "application programming interface": "api",
    "rest": "representational state transfer",
    "representational state transfer": "rest",
    "sql": "structured query language",
    "structured query language": "sql",
    "aws": "amazon web services",
    "amazon web services": "aws",
    "gcp": "google cloud platform",
    "google cloud platform": "gcp",
    "e2e": "end to end",
    "end to end": "e2e",
}

# If a project has any skill in the "trigger" set, also allow all skills in the "allow" set.
# This covers cases like: LangChain/RAG → obviously uses LLMs.
_SEMANTIC_CLUSTERS = [
    ({"langchain", "rag", "ai agents", "llm", "opentelemetry"}, {"langchain", "rag", "ai agents", "llm", "opentelemetry"}),
]


def _project_allowed_terms(project: dict) -> set[str]:
    """Build the full set of terms allowed for a project: its tech list,
    words from its description, acronym equivalents, and semantic clusters."""
    allowed = set()
    for t in project.get("tech", []):
        allowed.add(t.lower())
        if t.lower() in _ACRONYM_MAP:
            allowed.add(_ACRONYM_MAP[t.lower()])
    _STOP_WORDS_2 = {"is","in","at","by","to","an","on","of","or","as","it","be","we","us","no","my","up","if","do","so","go","he","she","me","am"}
    desc = project.get("description", "")
    for word in re.findall(r'\b[a-zA-Z]{2,}\b', desc.lower()):
        if len(word) > 2 or word not in _STOP_WORDS_2:
            allowed.add(word)
    # Acronym mappings for individual skills
    for cat_skills in _get_profile().get("skills", {}).values():
        for s in cat_skills:
            s_lower = s.lower()
            if s_lower in _ACRONYM_MAP and _ACRONYM_MAP[s_lower] in allowed:
                allowed.add(s_lower)
            if _ACRONYM_MAP.get(s_lower, "") in allowed:
                allowed.add(s_lower)
    # Semantic clusters: if project has ≥1 skill in trigger set, allow all in allow set
    project_tech_lower = {t.lower() for t in project.get("tech", [])}
    for trigger_set, allow_set in _SEMANTIC_CLUSTERS:
        if project_tech_lower & {t.lower() for t in trigger_set}:
            allowed.update({s.lower() for s in allow_set})
    return allowed


def _is_term_allowed(term: str, allowed: set[str]) -> bool:
    """Check if a (possibly multi-word) term is allowed.

    Allowed if:
    1. Term is directly in the allowed set, OR
    2. Every word is in allowed or maps to an allowed acronym, OR
    3. Any allowed term substantially overlaps with the term
       (e.g. 'rest api' is covered by 'django rest framework')."""
    if term in allowed:
        return True
    words = term.split()
    if len(words) > 1 and all(
        w in allowed or _ACRONYM_MAP.get(w, "") in allowed
        for w in words
    ):
        return True
    # Semantic overlap: if any allowed multi-word term contains ≥1 significant
    # word from the term, consider it covered.  Skip very short words.
    term_words = {w for w in words if len(w) >= 3}
    for allowed_term in allowed:
        allowed_words = set(allowed_term.split())
        if term_words & allowed_words:
            return True
    return False


_UNGROUNDED_CLAIM_PATTERNS = {
    "testing": {
        "vague_phrases": [
            r"writing (?:unit |integration |end-to-end |e2e )?tests?",
            r"comfortable with testing",
            r"full lifecycle.*testing",
            r"design through (?:production )?(?:rollout|testing)",
            r"participating in.*test",
            r"test(?:ing)? (?:practices|experience)",
        ],
        "grounding_keywords": [
            "pytest", "jest", "cypress", "playwright", "selenium", "unittest",
            "test suite", "ci test", "factory_boy", "pytest-django",
        ],
    },
    "monitoring": {
        "vague_phrases": [
            r"comfortable with monitoring", r"observability (?:practices|experience)",
        ],
        "grounding_keywords": [
            "prometheus", "grafana", "sentry", "datadog", "opentelemetry",
            "cloudwatch", "elk",
        ],
    },
    "security": {
        "vague_phrases": [
            r"security (?:practices|experience|best practices)",
            r"comfortable with security",
        ],
        "grounding_keywords": [
            "owasp", "penetration test", "vulnerability scan", "oauth", "jwt",
            "rbac", "encryption",
        ],
    },
}


def _build_profile_source_text() -> str:
    """Aggregate all PROFILE text into a single searchable string."""
    parts = []
    for p in _get_profile().get("projects", []):
        parts.append(p.get("description", ""))
        parts.append(" ".join(p.get("tech", [])))
    for e in _get_profile().get("experience", []):
        for v in e.values():
            if isinstance(v, str):
                parts.append(v)
    for cat_skills in _get_profile().get("skills", {}).values():
        parts.extend(cat_skills)
    return " ".join(parts).lower()


def _check_ungrounded_claims(letter_body: str) -> list[str]:
    """Detect vague skill-practice claims in the letter that have no
    grounding in the candidate's actual profile data."""
    issues = []
    profile_text = _build_profile_source_text()

    for category, cfg in _UNGROUNDED_CLAIM_PATTERNS.items():
        # Check if the letter makes a vague claim in this category
        claim_found = False
        for pattern in cfg["vague_phrases"]:
            if re.search(pattern, letter_body, re.IGNORECASE):
                claim_found = True
                break
        if not claim_found:
            continue

        # Check if the profile has ANY grounding keyword for this category
        has_grounding = any(
            kw in profile_text for kw in cfg["grounding_keywords"]
        )
        if not has_grounding:
            issues.append(f"ungrounded_claim:{category}")

    return issues


_PLACEHOLDER_DOMAINS = [
    "example.com", "yourportfolio.com", "yourcompany.com", "portfolio.com",
    "linkedin.com/in/yourname", "github.com/yourusername",
]

def _replace_placeholder_urls(text: str) -> str:
    profile = _get_profile()
    replacements = {}
    if profile.get("portfolio"):
        replacements["portfolio"] = profile["portfolio"]
    if profile.get("github"):
        replacements["github"] = profile["github"]
    if profile.get("linkedin"):
        replacements["linkedin"] = profile["linkedin"]

    for domain in _PLACEHOLDER_DOMAINS:
        pattern = re.escape(domain)
        text = re.sub(pattern, lambda m: _pick_replacement(m.group(), replacements), text, flags=re.IGNORECASE)
    return text


def _pick_replacement(matched: str, replacements: dict) -> str:
    matched_lower = matched.lower()
    for key, val in replacements.items():
        if key in matched_lower:
            return val
    return matched


def _validate_letter(letter: str, job) -> dict:
    """Run deterministic checks on a cover letter. Returns
    {"issues": [...], "repaired_letter": str}."""
    issues = []
    repaired = letter

    # --- a. SALUTATION CHECK ---
    if not repaired.startswith("Dear Hiring Manager,") and not repaired.startswith("Dear Hiring Manager ,"):
        issues.append("missing_salutation")
        repaired = "Dear Hiring Manager,\n\n" + repaired.lstrip()

    # --- b. SIGNATURE CHECK ---
    expected_sig = _build_signature()
    sig_lower = expected_sig.lower().split("\n")
    body_lines = repaired.rstrip().split("\n")
    while body_lines:
        line_stripped = body_lines[-1].strip().lower()
        if any(line_stripped == s for s in sig_lower if s):
            body_lines.pop()
        else:
            break
    body = "\n".join(body_lines).rstrip()
    if body != repaired.rstrip():
        issues.append("signature_repaired")
    repaired = body + "\n\n" + expected_sig

    # --- c. FORBIDDEN SKILL CHECK (body only, not signature) ---
    _, candidate_missing_str = _compute_skill_gap(job)
    if candidate_missing_str and not candidate_missing_str.startswith("None"):
        missing_skills = [s.strip() for s in candidate_missing_str.split(",")]
        sig_start = repaired.lower().rfind(expected_sig.split("\n")[0].lower())
        body_for_check = repaired[:sig_start] if sig_start > 0 else repaired
        for skill in missing_skills:
            if not skill:
                continue
            if re.search(rf"\b{re.escape(skill)}\b", body_for_check, re.IGNORECASE):
                issues.append(f"forbidden_skill:{skill}")

    # --- d. PROJECT ATTRIBUTION CHECK ---
    projects = _get_profile().get("projects", [])

    all_tech_terms = set()
    for p in projects:
        all_tech_terms.update(t.lower() for t in p.get("tech", []))
    for cat_skills in _get_profile().get("skills", {}).values():
        all_tech_terms.update(s.lower() for s in cat_skills)
    for term in list(all_tech_terms):
        if term in _ACRONYM_MAP:
            all_tech_terms.add(_ACRONYM_MAP[term])

    project_allowed = {}
    for p in projects:
        allowed = _project_allowed_terms(p)
        allowed_substrings = set()
        for t in allowed:
            for part in re.split(r'[\s/\-]+', t):
                if len(part) >= 3:
                    allowed_substrings.add(part)
        for term in list(all_tech_terms):
            if len(term) >= 3 and any(term in t for t in allowed if len(t) > len(term)):
                allowed_substrings.add(term)
        project_allowed[p["name"]] = allowed | allowed_substrings

    sentences = re.split(r'(?<=[.!?])\s+', repaired)
    sent_lower_cache = {}
    for sent in sentences:
        sent_lower = sent.lower()
        sent_lower_cache[sent] = sent_lower

        matched_projects = []
        for p in projects:
            if p["name"].lower() in sent_lower:
                matched_projects.append(p)

        if not matched_projects:
            if any(ref in sent_lower for ref in _AGGREGATE_REFERENCES):
                matched_projects = list(projects)

        if not matched_projects:
            continue

        for term in all_tech_terms:
            if term not in sent_lower:
                continue
            for p in matched_projects:
                if not _is_term_allowed(term, project_allowed[p["name"]]):
                    target = "+".join(p["name"] for p in matched_projects)
                    issues.append(f"misattribution:{term}->{target}")
                    break

    # --- e. NUMERIC CLAIM CHECK ---
    source_text = ""
    for p in projects:
        source_text += p.get("description", "") + " "
        source_text += " ".join(p.get("tech", [])) + " "
    for e in _get_profile().get("experience", []):
        source_text += e.get("company", "") + " "
        source_text += e.get("role", "") + " "
        source_text += e.get("duration", "") + " "
        source_text += e.get("location", "") + " "

    sig_start_idx = repaired.lower().rfind(expected_sig.split("\n")[0].lower())
    letter_body = repaired[:sig_start_idx].rstrip() if sig_start_idx > 0 else repaired

    number_patterns = re.findall(
        r'\b\d[\d,]*\.?\d*\s*%'
        r'|\b\d[\d,]*\.?\d*\s*(?:percent|percent)'
        r'|\b\d[\d,]*\.?\d*\s*[KkMm]\+?'
        r'|\b\d[\d,]*\.?\d*\s*ms\b'
        r'|\b\d[\d,]*\.?\d*\s*x\b',
        letter_body,
    )
    for match in number_patterns:
        normalized = re.sub(r'\s+', '', match.lower())
        raw_digits = re.sub(r'[^\d.]', '', match)
        if raw_digits and raw_digits not in source_text.lower():
            issues.append(f"unverified_number:{match.strip()}")

    # --- f. UNGROUNDED CLAIM CHECK (body only, not signature) ---
    issues.extend(_check_ungrounded_claims(letter_body))

    # --- g. PLACEHOLDER URL REPLACEMENT ---
    # Replace any placeholder/hallucinated URLs with the real ones from profile
    repaired = _replace_placeholder_urls(repaired)

    return {"issues": issues, "repaired_letter": repaired}


def _job_dict_with_ats(job, resume_text: str = "") -> dict:
    """Build the job dict for the cover letter engine, enriched with the CV
    engine's tier-derived missing keywords so the letter never claims skills
    the ATS analysis flags as missing."""
    job_dict = {
        "id": job.id,
        "company": job.company,
        "title": job.title,
        "location": job.location or "",
        "description": job.description or "",
        "matched_skills": job.matched_skills or [],
        "skill_gaps": job.skill_gaps or [],
    }
    try:
        from apps.jobs.services.cv_engine_client import get_ats_score
        profile = _get_profile()
        if resume_text:
            profile["resume_text"] = resume_text
        result = get_ats_score(job_dict, profile)
        ats = result.get("ats") or {}
        missing = ats.get("missing_keywords") or []
        if missing:
            job_dict["missing_keywords"] = missing
    except Exception as e:
        logger.debug(f"ATS report unavailable for cover letter job %d: %s", job.id, e)
    return job_dict


class GenerateCoverLetter(BaseAPIView):
    def post(self, request, job_id):
        job = get_object_or_404(Job.objects.select_related(), id=job_id)

        ai = AIConfig.load()
        if not ai.has_ai_config or not ai.get_api_key():
            # No LLM configured: degrade to the deterministic template letter
            # from the Cover Letter Engine (zero-config default).
            return self._generate_template(job)

        api_key = ai.get_api_key()
        if not api_key:
            return self.error(
                "Could not decrypt API key. Please re-save your AI Settings.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            resume_text = _extract_resume_text()
        except Exception:
            resume_text = ""

        job_dict = _job_dict_with_ats(job, resume_text)

        from apps.jobs.services.cover_letter_client import (
            CoverLetterEngineUnavailableError,
        )
        from apps.jobs.services.cover_letter_client import (
            generate_cover_letter as engine_generate,
        )

        try:
            result = engine_generate(
                job_dict,
                _get_profile(),
                mode="ai",
                resume_text=resume_text,
                ai_config={
                    "api_key": api_key,
                    "api_base_url": ai.api_base_url,
                    "model": ai.model_name,
                    "provider": ai.provider,
                },
            )
        except CoverLetterEngineUnavailableError:
            logger.warning("Cover letter engine down for job %d; using local LLM flow", job.id)
            return self._generate_locally(job, ai)

        cover_letter = result.get("cover_letter", "")
        if not cover_letter:
            return self._generate_locally(job, ai)

        existing_app = Application.objects.filter(job=job).first()
        if existing_app:
            existing_app.cover_letter_text = cover_letter
            existing_app.save(update_fields=["cover_letter_text"])

        return self.success({"cover_letter": cover_letter})

    def _generate_template(self, job):
        from apps.jobs.services.cover_letter_client import (
            CoverLetterEngineUnavailableError,
        )
        from apps.jobs.services.cover_letter_client import (
            generate_cover_letter as engine_generate,
        )

        job_dict = _job_dict_with_ats(job)

        try:
            result = engine_generate(job_dict, _get_profile(), mode="template")
            cover_letter = result.get("cover_letter", "")
        except CoverLetterEngineUnavailableError:
            cover_letter = ""

        if not cover_letter:
            return self.error(
                "AI not configured. Set your API key in Profile > AI Settings, or start "
                "the cover letter service.",
                status.HTTP_400_BAD_REQUEST,
            )

        existing_app = Application.objects.filter(job=job).first()
        if existing_app:
            existing_app.cover_letter_text = cover_letter
            existing_app.save(update_fields=["cover_letter_text"])

        return self.success({"cover_letter": cover_letter})

    def _generate_locally(self, job, ai):
        api_key = ai.get_api_key()

        system_prompt = _build_system_prompt()
        user_prompt = _build_user_prompt(job)

        cover_letter, llm_error = generate_with_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            api_key=api_key,
            api_base_url=ai.api_base_url,
            model=ai.model_name,
            provider=ai.provider,
            max_tokens=1000,
            timeout=30.0,
        )

        if not cover_letter:
            if llm_error and "413" in llm_error:
                msg = "Prompt too large for your model's token limit. Try a model with higher limits (e.g. Groq paid tier, DeepSeek, or OpenRouter) or switch to a model with a larger context window."
            elif llm_error and "429" in llm_error:
                msg = "Rate limited by your AI provider. Wait a moment and try again, or upgrade your plan."
            elif llm_error and "timeout" in llm_error.lower():
                msg = "AI request timed out. Try again."
            elif llm_error and "401" in llm_error:
                msg = "Invalid API key. Check your API key in Profile > AI Settings."
            else:
                msg = f"AI generation failed: {llm_error}" if llm_error else "AI generation failed. Check your API key and model in AI Settings."
            return self.error(msg, status.HTTP_502_BAD_GATEWAY)

        cover_letter = _clean_cover_letter(cover_letter)

        # --- Validation layer ---
        validation = _validate_letter(cover_letter, job)
        all_issues = validation["issues"]
        cover_letter = validation["repaired_letter"]

        if all_issues:
            logger.warning(
                "Validation issues for job %d (%s, model=%s): %s",
                job.id, job.company, ai.model_name, "; ".join(all_issues),
            )

        hard_issues = [
            i for i in all_issues
            if i.startswith(("forbidden_skill:", "misattribution:", "unverified_number:", "ungrounded_claim:"))
        ]

        # --- Retry once if hard issues found ---
        if hard_issues:
            retry_prompt = (
                f"Your previous attempt had these accuracy problems: "
                f"{'; '.join(hard_issues)}. Fix each one specifically in this attempt. "
                f"Do not repeat these errors. Remove any forbidden skills, correct "
                f"project attributions, remove or replace any unverified numbers, "
                f"and remove any vague skill claims that are not backed by a specific "
                f"tool, framework, or technique in the candidate's profile."
            )
            retry_system = system_prompt + "\n\n" + retry_prompt
            retry_letter, retry_error = generate_with_llm(
                system_prompt=retry_system,
                user_prompt=user_prompt,
                api_key=api_key,
                api_base_url=ai.api_base_url,
                model=ai.model_name,
                provider=ai.provider,
                max_tokens=1000,
                timeout=30.0,
            )

            if retry_letter:
                retry_letter = _clean_cover_letter(retry_letter)
                retry_validation = _validate_letter(retry_letter, job)
                retry_hard = [
                    i for i in retry_validation["issues"]
                    if i.startswith(("forbidden_skill:", "misattribution:", "unverified_number:", "ungrounded_claim:"))
                ]

                if retry_hard:
                    logger.warning(
                        "Retry still has hard issues for job %d (%s, model=%s): %s",
                        job.id, job.company, ai.model_name, "; ".join(retry_hard),
                    )
                    return Response(
                        {
                            "error": (
                                "AI generation had accuracy issues that could not be "
                                f"auto-corrected: {'; '.join(retry_hard)}. Try again, or "
                                "verify manually before sending."
                            ),
                            "draft_with_warnings": retry_validation["repaired_letter"],
                        },
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

                cover_letter = retry_validation["repaired_letter"]
                if retry_validation["issues"]:
                    logger.warning(
                        "Retry auto-fixed remaining issues for job %d (%s, model=%s): %s",
                        job.id, job.company, ai.model_name,
                        "; ".join(retry_validation["issues"]),
                    )

        # --- Final placeholder URL safety net ---
        cover_letter = _replace_placeholder_urls(cover_letter)

        coverage_warnings = _check_requirement_coverage(job, cover_letter)
        if coverage_warnings:
            logger.warning(
                "Requirement coverage warnings for job %d (%s): %s",
                job.id, job.company, "; ".join(coverage_warnings),
            )

        existing_app = Application.objects.filter(job=job).first()
        if existing_app:
            existing_app.cover_letter_text = cover_letter
            existing_app.save(update_fields=["cover_letter_text"])

        return self.success({"cover_letter": cover_letter})
