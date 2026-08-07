"""AI-mode cover-letter generation (OpenAI-compatible providers).

Faithful port of the working Django cover-letter flow
(``apps/jobs/views/cover_letter.py``): full grounded system prompt,
deterministic post-generation checks (salutation, signature, forbidden
skills, project attribution, numeric claims, ungrounded claims,
placeholder URLs), and a single auto-repair retry on hard issues.
Relocated unchanged into the engine service.
"""

# ruff: noqa: E501 — system/user prompt lines are verbatim prose

import logging
import re

import httpx

from coverletter.core.packs import pack_for_job

logger = logging.getLogger(__name__)

REASONING_MODELS = {
    "deepseek-r1",
    "qwq",
    "o1",
    "o3",
    "o4-mini",
    "qwen-qwq",
}

# Number of auto-repair attempts after the first validation fails on hard
# issues (forbidden skills, misattributions, unverified numbers, ungrounded
# claims). Each attempt re-runs the full validation.
AI_RETRY_LIMIT = 2


class AIGenerationError(Exception):
    pass


def _signature(profile: dict) -> str:
    name = profile.get("name", "Developer")
    phone = profile.get("phone", "")
    portfolio = profile.get("portfolio", "")
    github = profile.get("github", "")
    linkedin = profile.get("linkedin", "")

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


def _compute_skill_gap(job: dict, profile: dict) -> tuple[str, str]:
    candidate_skills_lower = set()
    for cat_skills in (profile.get("skills") or {}).values():
        for s in cat_skills:
            candidate_skills_lower.add(s.lower())

    has_set = set(job.get("matched_skills") or [])
    missing_set = set(job.get("skill_gaps") or [])

    # Prefer the CV engine's tier-derived missing keywords when supplied.
    engine_missing = job.get("missing_keywords") or []
    missing_set.update(engine_missing)

    desc = (job.get("description") or "").lower()
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
    missing_text = (
        ", ".join(missing_list) if missing_list
        else "None -- candidate matches all listed requirements"
    )
    return has_text, missing_text


_PROFESSION_LABELS = {
    "healthcare": "healthcare",
    "education": "education",
    "finance_accounting": "finance and accounting",
    "it_software": "software development",
    "engineering": "engineering",
    "marketing_sales": "marketing and sales",
    "hospitality": "hospitality",
    "trades_construction": "trades and construction",
    "design_creative": "design and creative",
    "legal": "legal",
    "admin_operations": "administration and operations",
    "science_research": "science and research",
    "retail_customer_service": "retail and customer service",
    "hr_people": "HR and people operations",
}


def _detected_profession(job: dict, profile: dict) -> str:
    """Human label for the best-matching profession pack (prompt input)."""
    try:
        pack = pack_for_job(job, profile)
    except Exception:
        return "software development"
    pack_id = pack.get("id", "neutral")
    if pack_id == "it_software":
        return "software development"
    if pack_id == "neutral":
        return "a professional"
    return _PROFESSION_LABELS.get(pack_id, "a professional")


def _build_system_prompt(signature: str, profession: str = "software development") -> str:
    if profession and profession != "a professional":
        opener = f"You are a professional cover letter writer for {profession} roles."
    else:
        opener = "You are a professional cover letter writer."
    return f"""{opener}

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

PARAGRAPH SEPARATION RULE:
- Each distinct project or experience you discuss must be its own paragraph, separated by a blank line. Never describe two different projects in the same paragraph.
- The letter must have clearly separated paragraphs: salutation, opening (JD alignment), one paragraph per project/experience discussed (usually 1-2 total), and a distinct closing paragraph. Never merge the closing statement into the same paragraph as a technical detail.
- The closing paragraph must be its own paragraph, end with a forward-looking statement (e.g. 'I'd welcome the chance to discuss...'), and must not be the same sentence as the last technical point.

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
- Do not write blanket claims like 'Both projects run on X' or 'Both projects include Y' unless X or Y is specifically true for each project individually and is a specific, nameable tool or practice -- not a vague category like 'automated testing' with no named framework.

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
- Do not write blanket claims like 'Both projects run on X' or 'Both projects include Y' unless X or Y is specifically true for each project individually and is a specific, nameable tool or practice -- not a vague category like 'automated testing' with no named framework.

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


def _build_user_prompt(job: dict, profile: dict, profession: str = "a professional") -> str:
    name = profile.get("name", "Candidate")
    location = profile.get("location", "Not specified")
    role = profile.get("role", "a professional")
    experience_years = profile.get("experience_years", 1)

    experience = profile.get("experience", [])
    exp_text = ""
    if experience:
        e = experience[0]
        exp_text = f"{e.get('role', role)} at {e.get('company', 'Unknown')}, {e.get('location', location)}"
        if e.get("duration"):
            exp_text += f" ({e['duration']})"

    desc = (job.get("description") or "")[:3000]

    candidate_has, candidate_missing = _compute_skill_gap(job, profile)

    projects_text = ""
    for p in profile.get("projects", []):
        projects_text += (
            f"- {p.get('name', '')}: {p.get('description', '')} "
            f"(Tech: {', '.join(p.get('tech', [])[:8])})\n"
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

    urls_text = []
    if profile.get("portfolio"):
        urls_text.append(f"Portfolio: {profile['portfolio']}")
    if profile.get("github"):
        urls_text.append(f"GitHub: {profile['github']}")
    if profile.get("linkedin"):
        urls_text.append(f"LinkedIn: {profile['linkedin']}")
    urls_block = "\n".join(urls_text) if urls_text else "None provided"

    return f"""Write a cover letter for this specific job application.

JOB:
Company: {job.get('company', '')}
Title: {job.get('title', '')}
Location: {job.get('location') or 'Not specified'}

JOB DESCRIPTION:
{desc}

CANDIDATE:
Name: {name}
Role: {role}
DETECTED PROFESSION: {profession}
Experience: {experience_years} year(s) -- {exp_text}
CANDIDATE TOTAL EXPERIENCE: {experience_years} year(s)
CANDIDATE LOCATION: {profile.get('location', 'Not specified')}
OPEN TO RELOCATION: {profile.get('open_to_relocation', 'Not specified')}
CANDIDATE AVAILABILITY: {profile.get('availability', 'Not specified')}
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


def _clean(text: str) -> str:
    text = re.sub(r"\s*--\s*", ", ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# --- Output cleaning (same as Django apps/jobs/llm_client.py) ---------------

def _strip_think_tags(text: str) -> str:
    text = re.sub(r"<think>[\s\S]*?</think>?", "", text)
    text = re.sub(r"<thinking>[\s\S]*?</thinking>?", "", text)
    text = re.sub(r"<thought>[\s\S]*?</thought>?", "", text)
    text = re.sub(r"^\s*\d+\.\s+\*{2}.*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _strip_output_artifacts(text: str) -> str:
    text = re.sub(
        r"^(?:Cover Letter|Here(?:'s| is) (?:your |a )?cover letter|Generated Cover Letter)\s*[:\-]?\s*\n",
        "",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    text = re.sub(r"^#{1,3}\s+.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\*{1,2}(.*?)\*{1,2}$", r"\1", text, flags=re.MULTILINE)
    if text.startswith('"') and text.endswith('"') and len(text.split("\n")) > 3:
        text = text[1:-1]
    return text.strip()


def _is_usable(text: str) -> bool:
    return bool(text) and len(text.split()) >= 50


def _detect_reasoning_model(model: str) -> bool:
    model_lower = model.lower()
    return any(alias in model_lower for alias in REASONING_MODELS)


# --- Deterministic validation (same as Django cover_letter.py) --------------

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

# If a project has any skill in the "trigger" set, also allow all skills in the
# "allow" set. This covers cases like: LangChain/RAG -> obviously uses LLMs.
_SEMANTIC_CLUSTERS = [
    ({"langchain", "rag", "ai agents", "llm", "opentelemetry"}, {"langchain", "rag", "ai agents", "llm", "opentelemetry"}),
]

# Dev tools used by essentially every software project. Allowed for any
# project only when the candidate claims the skill in their profile, so a
# sentence like "I used git on DENJO-C" is not flagged as misattribution.
_UNIVERSAL_TOOLS = {
    "git", "github", "github actions", "ci/cd", "docker", "docker compose",
}

# Infrastructure / hosting implied by a listed technology (RDS hosts
# PostgreSQL, Vercel hosts React apps, ...). Only applied when the candidate
# also claims the implied skill, preventing false misattribution flags.
_IMPLIED_TECH = {
    "django": {"gunicorn", "drf"},
    "drf": {"django"},
    "postgresql": {"rds"},
    "redis": {"elasticache"},
    "aws": {"ec2", "s3", "iam", "cloudfront", "elasticache", "rds"},
    "react": {"react.js", "vite", "vercel"},
    "react.js": {"react", "vercel"},
    "llm": {"groq", "openai", "rag", "langchain", "ai agents"},
    "groq": {"llm"},
}

_COVERAGE_KEYWORDS = {
    "test": ["test", "testing", "unit test", "integration test", "end-to-end", "e2e"],
    "ci/cd": ["ci/cd", "ci cd", "continuous integration", "continuous deployment", "pipeline"],
    "security": ["security", "compliance", "owasp", "vulnerability", "authentication"],
    "accessibility": ["accessibility", "a11y", "wcag", "screen reader"],
    "monitoring": ["monitoring", "observability", "logging", "alerting", "apm"],
    "documentation": ["documentation", "docs", "technical writing"],
    "agile": ["agile", "scrum", "sprint", "kanban"],
}

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

_PLACEHOLDER_DOMAINS = [
    "example.com", "yourportfolio.com", "yourcompany.com", "portfolio.com",
    "linkedin.com/in/yourname", "github.com/yourusername",
]


def _project_allowed_terms(project: dict, profile: dict) -> set[str]:
    allowed = set()
    for t in project.get("tech", []):
        allowed.add(t.lower())
        if t.lower() in _ACRONYM_MAP:
            allowed.add(_ACRONYM_MAP[t.lower()])
    stop_words_2 = {"is", "in", "at", "by", "to", "an", "on", "of", "or", "as", "it", "be", "we", "us", "no", "my", "up", "if", "do", "so", "go", "he", "she", "me", "am"}
    desc = project.get("description", "")
    for word in re.findall(r'\b[a-zA-Z]{2,}\b', desc.lower()):
        if len(word) > 2 or word not in stop_words_2:
            allowed.add(word)
    # Acronym mappings for individual skills
    for cat_skills in (profile.get("skills") or {}).values():
        for s in cat_skills:
            s_lower = s.lower()
            if s_lower in _ACRONYM_MAP and _ACRONYM_MAP[s_lower] in allowed:
                allowed.add(s_lower)
            if _ACRONYM_MAP.get(s_lower, "") in allowed:
                allowed.add(s_lower)
    # Semantic clusters: if project has >=1 skill in trigger set, allow all in allow set
    project_tech_lower = {t.lower() for t in project.get("tech", [])}
    for trigger_set, allow_set in _SEMANTIC_CLUSTERS:
        if project_tech_lower & {t.lower() for t in trigger_set}:
            allowed.update({s.lower() for s in allow_set})
    # Universal tooling + infra implied by listed tech (git, RDS for
    # PostgreSQL, Vercel for React, ...): allowed only when the candidate
    # claims the skill in their profile, so true statements are not flagged.
    profile_skills = set()
    for cat_skills in (profile.get("skills") or {}).values():
        profile_skills.update(s.lower() for s in cat_skills)
    for tool in _UNIVERSAL_TOOLS:
        if tool in profile_skills:
            allowed.add(tool)
    for tech in project_tech_lower:
        for implied in _IMPLIED_TECH.get(tech, ()):
            if implied in profile_skills:
                allowed.add(implied)
    return allowed


def _is_term_allowed(term: str, allowed: set[str]) -> bool:
    if term in allowed:
        return True
    words = term.split()
    if len(words) > 1 and all(
        w in allowed or _ACRONYM_MAP.get(w, "") in allowed
        for w in words
    ):
        return True
    # Semantic overlap: if any allowed multi-word term contains >=1 significant
    # word from the term, consider it covered. Skip very short words.
    term_words = {w for w in words if len(w) >= 3}
    for allowed_term in allowed:
        allowed_words = set(allowed_term.split())
        if term_words & allowed_words:
            return True
    return False


def _build_profile_source_text(profile: dict) -> str:
    parts = []
    for p in profile.get("projects", []):
        parts.append(p.get("description", ""))
        parts.append(" ".join(p.get("tech", [])))
    for e in profile.get("experience", []):
        for v in e.values():
            if isinstance(v, str):
                parts.append(v)
    for cat_skills in (profile.get("skills") or {}).values():
        parts.extend(cat_skills)
    return " ".join(parts).lower()


def _check_ungrounded_claims(letter_body: str, profile: dict) -> list[str]:
    issues = []
    profile_text = _build_profile_source_text(profile)

    for category, cfg in _UNGROUNDED_CLAIM_PATTERNS.items():
        claim_found = False
        for pattern in cfg["vague_phrases"]:
            if re.search(pattern, letter_body, re.IGNORECASE):
                claim_found = True
                break
        if not claim_found:
            continue

        has_grounding = any(kw in profile_text for kw in cfg["grounding_keywords"])
        if not has_grounding:
            issues.append(f"ungrounded_claim:{category}")

    return issues


def _replace_placeholder_urls(text: str, profile: dict) -> str:
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


def _check_requirement_coverage(job: dict, letter: str) -> list[str]:
    warnings = []
    desc = (job.get("description") or "").lower()
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
            warnings.append(f"JD requires '{category}' but letter does not address it")

    return warnings


def _validate(letter: str, job: dict, profile: dict, signature: str) -> tuple[str, list[str]]:
    """Run deterministic checks on a cover letter. Returns (repaired, issues)."""
    issues = []
    repaired = letter

    # --- a. SALUTATION CHECK ---
    if not repaired.startswith("Dear Hiring Manager,") and not repaired.startswith("Dear Hiring Manager ,"):
        issues.append("missing_salutation")
        repaired = "Dear Hiring Manager,\n\n" + repaired.lstrip()

    # --- b. SIGNATURE CHECK ---
    sig_lower = [s for s in signature.lower().split("\n") if s]
    body_lines = repaired.rstrip().split("\n")
    while body_lines:
        line_stripped = body_lines[-1].strip().lower()
        # Pop exact signature lines and truncated fragments ("Port" is a partial
        # "Portfolio: ..."), so a cut-off signature is replaced, not duplicated.
        if any(
            line_stripped == s or (len(line_stripped) >= 3 and s.startswith(line_stripped))
            for s in sig_lower
        ):
            body_lines.pop()
        else:
            break
    body = "\n".join(body_lines).rstrip()
    if body != repaired.rstrip():
        issues.append("signature_repaired")
    repaired = body + "\n\n" + signature

    # --- c. FORBIDDEN SKILL CHECK (body only, not signature) ---
    _, candidate_missing_str = _compute_skill_gap(job, profile)
    if candidate_missing_str and not candidate_missing_str.startswith("None"):
        missing_skills = [s.strip() for s in candidate_missing_str.split(",")]
        sig_start = repaired.lower().rfind(signature.split("\n")[0].lower())
        body_for_check = repaired[:sig_start] if sig_start > 0 else repaired
        for skill in missing_skills:
            if not skill:
                continue
            if re.search(rf"\b{re.escape(skill)}\b", body_for_check, re.IGNORECASE):
                issues.append(f"forbidden_skill:{skill}")

    # --- d. PROJECT ATTRIBUTION CHECK ---
    projects = profile.get("projects", [])

    all_tech_terms = set()
    for p in projects:
        all_tech_terms.update(t.lower() for t in p.get("tech", []))
    for cat_skills in (profile.get("skills") or {}).values():
        all_tech_terms.update(s.lower() for s in cat_skills)
    for term in list(all_tech_terms):
        if term in _ACRONYM_MAP:
            all_tech_terms.add(_ACRONYM_MAP[term])

    # Skills the candidate lists only as general capabilities (not tied to any
    # specific project) are allowed anywhere: mentioning them next to a project
    # name is a claim about the candidate, not an attribution to the project.
    project_tech_union = set()
    for p in projects:
        project_tech_union.update(t.lower() for t in p.get("tech", []))
    general_skills = set()
    for cat_skills in (profile.get("skills") or {}).values():
        for s in cat_skills:
            s_lower = s.lower()
            if s_lower not in project_tech_union:
                general_skills.add(s_lower)

    project_allowed = {}
    for p in projects:
        allowed = _project_allowed_terms(p, profile)
        allowed_substrings = set()
        for t in allowed:
            for part in re.split(r'[\s/\-]+', t):
                if len(part) >= 3:
                    allowed_substrings.add(part)
        for term in list(all_tech_terms):
            if len(term) >= 3 and any(term in t for t in allowed if len(t) > len(term)):
                allowed_substrings.add(term)
        project_allowed[p.get("name", "")] = allowed | allowed_substrings

    sentences = re.split(r'(?<=[.!?])\s+', repaired)
    for sent in sentences:
        sent_lower = sent.lower()

        matched_projects = []
        for p in projects:
            if p.get("name", "").lower() in sent_lower:
                matched_projects.append(p)

        if not matched_projects:
            if any(ref in sent_lower for ref in _AGGREGATE_REFERENCES):
                matched_projects = list(projects)

        if not matched_projects:
            continue

        for term in all_tech_terms:
            if term not in sent_lower:
                continue
            if term in general_skills:
                continue
            # A term mentioned alongside several projects is fine when it is
            # allowed for at least one of them ("I built PyDocAI and DENJO-C
            # with JWT"): the sentence may only claim it for one project.
            if any(
                _is_term_allowed(term, project_allowed.get(p.get("name", ""), set()))
                for p in matched_projects
            ):
                continue
            target = "+".join(p.get("name", "") for p in matched_projects)
            issues.append(f"misattribution:{term}->{target}")

    # --- e. NUMERIC CLAIM CHECK ---
    source_text = ""
    for p in projects:
        source_text += p.get("description", "") + " "
        source_text += " ".join(p.get("tech", [])) + " "
    for e in profile.get("experience", []):
        source_text += e.get("company", "") + " "
        source_text += e.get("role", "") + " "
        source_text += e.get("duration", "") + " "
        source_text += e.get("location", "") + " "

    sig_start_idx = repaired.lower().rfind(signature.split("\n")[0].lower())
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
        raw_digits = re.sub(r'[^\d.]', '', match)
        if raw_digits and raw_digits not in source_text.lower():
            issues.append(f"unverified_number:{match.strip()}")

    # --- f. UNGROUNDED CLAIM CHECK (body only, not signature) ---
    issues.extend(_check_ungrounded_claims(letter_body, profile))

    # --- g. PLACEHOLDER URL REPLACEMENT ---
    repaired = _replace_placeholder_urls(repaired, profile)

    return repaired, issues


def _call_llm(system_prompt: str, user_prompt: str, api_key: str, api_base_url: str,
              model: str, provider: str = "", max_tokens: int = 1000, timeout: float = 30.0) -> str:
    url = f"{api_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if "openrouter" in api_base_url.lower():
        headers["HTTP-Referer"] = "https://pathfinder.dev"
        headers["X-Title"] = "JobbLoot"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    if _detect_reasoning_model(model):
        payload["reasoning"] = {"enabled": False}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException:
        raise AIGenerationError("AI request timed out. Try again.")
    except Exception as e:
        raise AIGenerationError(f"exception: {e}")

    if resp.status_code == 413:
        raise AIGenerationError("413")
    if resp.status_code == 429:
        raise AIGenerationError("429")
    if resp.status_code == 401:
        raise AIGenerationError("401")
    resp.raise_for_status()

    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        raise AIGenerationError("no choices returned")

    choice = choices[0]
    message = choice.get("message", {})
    finish_reason = choice.get("finish_reason", "unknown")

    reasoning = message.get("reasoning_content", "") or ""
    content = message.get("content", "") or ""
    if not content and reasoning:
        raise AIGenerationError(f"reasoning-only (finish_reason={finish_reason})")

    result = _strip_output_artifacts(_strip_think_tags(content.strip()))
    if not _is_usable(result):
        raise AIGenerationError(f"output_too_short (finish_reason={finish_reason})")

    return result


def generate_ai_letter(job: dict, profile: dict, ai: dict,
                       resume_text: str = "") -> tuple[str, list[str]]:
    api_key = (ai or {}).get("api_key", "")
    api_base_url = (ai or {}).get("api_base_url", "")
    model = (ai or {}).get("model", "")
    provider = (ai or {}).get("provider", "")
    if not api_key or not api_base_url or not model:
        raise AIGenerationError("ai_config_incomplete")

    signature = _signature(profile)
    profession = _detected_profession(job, profile)
    system_prompt = _build_system_prompt(signature, profession)
    user_prompt = _build_user_prompt(job, profile, profession)

    letter = _call_llm(system_prompt, user_prompt, api_key, api_base_url, model, provider)
    letter = _clean(letter)

    letter, issues = _validate(letter, job, profile, signature)

    hard_issues = [
        i for i in issues
        if i.startswith(("forbidden_skill:", "misattribution:", "unverified_number:", "ungrounded_claim:"))
    ]

    retries = 0
    while hard_issues and retries < AI_RETRY_LIMIT:
        retries += 1
        retry_note = (
            f"Your previous attempt had these accuracy problems: "
            f"{'; '.join(hard_issues)}. Fix each one specifically in this attempt. "
            f"Do not repeat these errors. Remove any forbidden skills, correct "
            f"project attributions, remove or replace any unverified numbers, "
            f"and remove any vague skill claims that are not backed by a specific "
            f"tool, framework, or technique in the candidate's profile."
        )
        retry_system = system_prompt + "\n\n" + retry_note
        retry_letter = _call_llm(retry_system, user_prompt, api_key, api_base_url, model, provider)
        retry_letter = _clean(retry_letter)
        retry_letter, retry_issues = _validate(retry_letter, job, profile, signature)
        hard_issues = [
            i for i in retry_issues
            if i.startswith(("forbidden_skill:", "misattribution:", "unverified_number:", "ungrounded_claim:"))
        ]
        if hard_issues and retries < AI_RETRY_LIMIT:
            continue

        letter, issues = retry_letter, retry_issues
        if hard_issues:
            logger.warning(
                "AI cover letter retry still has hard issues for %s (%s): %s",
                job.get("title"), job.get("company"), "; ".join(hard_issues),
            )
            raise AIGenerationError(
                "AI generation had accuracy issues that could not be auto-corrected: "
                f"{'; '.join(hard_issues)}. Try again, or verify manually before sending."
            )
        if issues:
            logger.warning(
                "AI cover letter retry auto-fixed remaining issues for %s (%s): %s",
                job.get("title"), job.get("company"), "; ".join(issues),
            )
        break

    coverage_warnings = _check_requirement_coverage(job, letter)
    if coverage_warnings:
        logger.warning(
            "Requirement coverage warnings for %s (%s): %s",
            job.get("title"), job.get("company"), "; ".join(coverage_warnings),
        )

    return letter, issues
