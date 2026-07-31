"""AI-mode cover-letter generation (OpenAI-compatible providers).

Ported from the Django cover-letter view: builds a strict, grounded
system prompt, calls the provider's /chat/completions endpoint, then runs
deterministic checks (salutation, forbidden skills, signature, numeric
claims, placeholder URLs) with a single auto-repair retry.
"""

# ruff: noqa: E501 — system/user prompt lines are verbatim prose

import logging
import re

import httpx

logger = logging.getLogger(__name__)


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


def _build_system_prompt(signature: str) -> str:
    return f"""You are a professional cover letter writer.

OUTPUT RULES:
- Output ONLY the cover letter. No labels, no analysis, no commentary.
- NEVER output <think> or <thinking> or <thought> tags. Just the letter itself.
- The letter must always begin with the line "Dear Hiring Manager," -- never omit this.
- NEVER use "I am writing to express my interest" or "I am excited to apply".
- NEVER use emojis, markdown formatting, bold, bullet points, or dashes (--) around descriptions.
- Plain text only, ATS-friendly.

STRUCTURE (4-5 short paragraphs, under 180 words body):
1. SALUTATION (mandatory, always first): exactly "Dear Hiring Manager," on its own line, followed by a blank line.
2. Opening paragraph: reference something SPECIFIC from the job description -- a named technology they use, the domain they operate in, or a problem they describe. Vary your opening sentence.
3. Body: connect your most relevant project(s) and skills to what this specific job needs.
4. Closing: a brief, confident close. Vary it between letters.
Then append the signature block exactly as given in the SIGNATURE section below, on a new line after the closing paragraph.

BANNED:
- "I am genuinely interested in contributing to X and happy to discuss how I can add value from day one"
- "I am writing to express my interest in the X position"
- "Dear Hiring Manager at {{company}}" -- always use exactly "Dear Hiring Manager,".
- Any sentence that could apply to literally any job without changes.
- Passive or indirect openers. Open with a direct, confident statement connecting a specific JD detail to a specific thing you have built or done -- active voice.
- Stacking more than one soft/eager phrase in the same letter. Pick the single strongest one and cut the rest.
- Generic closing lines like "I look forward to discussing my qualifications further".

NO REPETITION:
- Do not repeat any phrase, sentence fragment, or distinctive wording from the job description more than once in the entire letter.
- The closing paragraph must reference something specific and different from what was already said.

ACRONYM RULES:
- Never expand, define, or explain an acronym or technical term unless the exact expansion is explicitly given in the job description or candidate profile provided to you.
- This applies especially to RAG -- write 'RAG' alone, exactly as given, with no parenthetical expansion, ever.

SKILL GAP RULE -- MANDATORY, NON-NEGOTIABLE:
You are given two lists: SKILLS THE CANDIDATE HAS THAT MATCH THIS JOB, and SKILLS THIS JOB REQUIRES THAT THE CANDIDATE DOES NOT HAVE.
- You may ONLY write about skills from the first list as things the candidate has, uses, or has experience with.
- Every skill name in the second list is FORBIDDEN to appear anywhere in your output, in any form.
- Before you finalize your response, re-read it and check: does any sentence contain a word from the missing-skills list? If yes, rewrite that sentence.

NUMERIC CLAIM RULE -- MANDATORY, NON-NEGOTIABLE:
- Every number, percentage, statistic, or measurable claim in your output must appear VERBATIM in the PROJECTS or EXPERIENCE data given to you below, attached to the exact same achievement it describes there.
- You are FORBIDDEN from moving a number from one achievement to a different achievement, combining two numbers, rounding a number, or inventing a new number.
- If no specific number supports the point you want to make, make the point WITHOUT a number.

GROUNDED CLAIM RULE -- MANDATORY:
- Every claim about a skill, practice, or capability must be backed by something specific in the candidate's PROJECTS or EXPERIENCE data below -- not just a general category match.
- Do NOT write soft, unverifiable claims like "I'm comfortable with testing" unless the source data actually names a specific tool, framework, or practice.
- If the job requires a skill that has no specific, nameable backing in the candidate's data, do NOT mention that skill at all, vague or otherwise.

JD TECHNOLOGY LIST RULE:
- When the job description lists multiple technologies together, you may NEVER claim the full list as something you have experience with as a group.
- Check each individual item against the candidate's actual PROJECTS and EXPERIENCE data. Only mention the specific items that are individually present. Drop the rest silently.

PROJECT ATTRIBUTION RULE:
- Each project can only be described using the technologies and responsibilities listed for that specific project in the PROJECTS section of the prompt.
- Never write "in Project X, I used Skill Y" if Skill Y does not appear in Project X's Tech line.

LOCATION RULE:
- Only make a claim about relocation, remote availability, or being 'based in' a location if the candidate's actual location and relocation preference are given explicitly below.
- Never name a specific city as a place the candidate is 'ready to relocate to' unless that is the job's actual stated location AND the candidate's relocation preference explicitly allows it.

AVAILABILITY RULE:
- Only make a claim about notice period, start date, or ability to join immediately if the candidate's actual availability is given explicitly below.

SENIORITY AWARENESS RULE:
- If the job title includes a seniority marker (Senior, Staff, Lead, Principal, etc.) and the candidate's total experience is under 3 years, do not write the letter as if seniority is a non-issue. Make the strongest honest case that complexity of work compensates for fewer years, using only real details from the candidate's data.

TONE -- WRITE LIKE A HUMAN, NOT AN AI:
- Write the way a sharp professional would actually write to a hiring manager they respect -- direct, specific, not corporate-polished.
- Vary sentence length deliberately. Avoid three sentences in a row with the same length and structure.
- Do not use inflated adjectives that add no information: 'passionate', 'thrilled', 'excited to leverage', 'robust', 'seamless', 'cutting-edge', 'dynamic', 'comprehensive'.
- Do not use symmetric three-part lists for their own rhythm.
- Avoid corporate transition phrases: 'Furthermore', 'Moreover', 'In addition to this'.
- Every sentence should contain either a specific technical detail, a real outcome, or a direct connection to something the job actually asks for.

SIGNATURE (append exactly as-is after the closing paragraph):
{signature}

FINAL CHECK (do this silently before outputting):
- Re-read your full draft once for spelling and word-choice errors. Fix any you find.
- Confirm every technology name is spelled correctly.
- Confirm the letter still satisfies every rule above (grounded claims, no repeated JD phrases, salutation present, signature intact, no fabricated numbers).
- Only output the final, corrected version -- never show your proofreading process."""


def _build_user_prompt(job: dict, profile: dict) -> str:
    name = profile.get("name", "Developer")
    location = profile.get("location", "India")
    role = profile.get("role", "Professional")
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
            f"- {p['name']}: {p.get('description', '')} "
            f"(Tech: {', '.join(p.get('tech', [])[:8])})\n"
        )

    experience_text = ""
    for e in experience:
        experience_text += (
            f"- {e.get('role', role)} at {e.get('company', 'Unknown')}, {e.get('location', location)}"
        )
        if e.get("duration"):
            experience_text += f" ({e['duration']})"
        experience_text += "\n"

    urls_text = []
    for key, label in (("portfolio", "Portfolio"), ("github", "GitHub"), ("linkedin", "LinkedIn")):
        if profile.get(key):
            urls_text.append(f"{label}: {profile[key]}")
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


def _replace_placeholder_urls(text: str, profile: dict) -> str:
    replacements = {}
    if profile.get("portfolio"):
        replacements["portfolio"] = profile["portfolio"]
    if profile.get("github"):
        replacements["github"] = profile["github"]
    if profile.get("linkedin"):
        replacements["linkedin"] = profile["linkedin"]

    domains = [
        "example.com", "yourportfolio.com", "yourcompany.com", "portfolio.com",
        "linkedin.com/in/yourname", "github.com/yourusername",
    ]

    def _pick(matched: str) -> str:
        lower = matched.lower()
        for key, val in replacements.items():
            if key in lower:
                return val
        return matched

    for domain in domains:
        text = re.sub(re.escape(domain), _pick, text, flags=re.IGNORECASE)
    return text


def _validate(letter: str, job: dict, profile: dict, signature: str) -> tuple[str, list[str]]:
    issues = []
    repaired = letter

    if not repaired.startswith("Dear Hiring Manager,"):
        issues.append("missing_salutation")
        repaired = "Dear Hiring Manager,\n\n" + repaired.lstrip()

    sig_lower = signature.lower().split("\n")
    body_lines = repaired.rstrip().split("\n")
    while body_lines:
        stripped = body_lines[-1].strip().lower()
        if any(stripped == s for s in sig_lower if s):
            body_lines.pop()
        else:
            break
    body = "\n".join(body_lines).rstrip()
    if body != repaired.rstrip():
        issues.append("signature_repaired")
    repaired = body + "\n\n" + signature

    _, candidate_missing_str = _compute_skill_gap(job, profile)
    if candidate_missing_str and not candidate_missing_str.startswith("None"):
        missing_skills = [s.strip() for s in candidate_missing_str.split(",")]
        sig_start = repaired.lower().rfind(signature.split("\n")[0].lower())
        body_for_check = repaired[:sig_start] if sig_start > 0 else repaired
        for skill in missing_skills:
            if skill and re.search(rf"\b{re.escape(skill)}\b", body_for_check, re.IGNORECASE):
                issues.append(f"forbidden_skill:{skill}")

    source_text = ""
    for p in profile.get("projects", []):
        source_text += p.get("description", "") + " "
        source_text += " ".join(p.get("tech", [])) + " "
    for e in profile.get("experience", []):
        source_text += " ".join(str(v) for v in e.values()) + " "

    sig_start_idx = repaired.lower().rfind(signature.split("\n")[0].lower())
    letter_body = repaired[:sig_start_idx].rstrip() if sig_start_idx > 0 else repaired
    number_patterns = re.findall(
        r"\b\d[\d,]*\.?\d*\s*%"
        r"|\b\d[\d,]*\.?\d*\s*(?:percent|percent)"
        r"|\b\d[\d,]*\.?\d*\s*[KkMm]\+?"
        r"|\b\d[\d,]*\.?\d*\s*ms\b"
        r"|\b\d[\d,]*\.?\d*\s*x\b",
        letter_body,
    )
    for match in number_patterns:
        raw_digits = re.sub(r"[^\d.]", "", match)
        if raw_digits and raw_digits not in source_text.lower():
            issues.append(f"unverified_number:{match.strip()}")

    return _replace_placeholder_urls(repaired, profile), issues


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
        "temperature": 0.4,
    }
    resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
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
        raise AIGenerationError("no_choices")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise AIGenerationError("empty_content")
    return content


def generate_ai_letter(job: dict, profile: dict, ai: dict,
                       resume_text: str = "") -> tuple[str, list[str]]:
    api_key = (ai or {}).get("api_key", "")
    api_base_url = (ai or {}).get("api_base_url", "")
    model = (ai or {}).get("model", "")
    provider = (ai or {}).get("provider", "")
    if not api_key or not api_base_url or not model:
        raise AIGenerationError("ai_config_incomplete")

    signature = _signature(profile)
    system_prompt = _build_system_prompt(signature)
    user_prompt = _build_user_prompt(job, profile)

    letter = _call_llm(system_prompt, user_prompt, api_key, api_base_url, model, provider)
    letter = _clean(letter)
    letter, issues = _validate(letter, job, profile, signature)

    hard_issues = [
        i for i in issues
        if i.startswith(("forbidden_skill:", "unverified_number:"))
    ]
    if hard_issues:
        retry_note = (
            f"Your previous attempt had these accuracy problems: "
            f"{'; '.join(hard_issues)}. Fix each one specifically in this attempt. "
            f"Do not repeat these errors."
        )
        retry_system = system_prompt + "\n\n" + retry_note
        retry_letter = _call_llm(retry_system, user_prompt, api_key, api_base_url, model, provider)
        retry_letter = _clean(retry_letter)
        retry_letter, retry_issues = _validate(retry_letter, job, profile, signature)
        retry_hard = [
            i for i in retry_issues
            if i.startswith(("forbidden_skill:", "unverified_number:"))
        ]
        if not retry_hard:
            letter, issues = retry_letter, retry_issues

    return letter, issues
