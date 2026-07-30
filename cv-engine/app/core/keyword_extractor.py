from app.config import SKILL_WEIGHTS, SKILL_ALIASES, SKILL_CATEGORIES


def extract_jd_keywords(jd_text: str) -> dict:
    jd_lower = jd_text.lower()
    must_have = []
    nice_to_have = []
    tools = []
    concepts = []
    soft_skills = []

    for skill, weight in SKILL_WEIGHTS.items():
        aliases = [skill] + SKILL_ALIASES.get(skill, [])
        for alias in aliases:
            if alias in jd_lower:
                if skill in [s.lower() for s in SKILL_CATEGORIES.get("must_have", [])]:
                    must_have.append(skill)
                elif skill in [s.lower() for s in SKILL_CATEGORIES.get("nice_to_have", [])]:
                    nice_to_have.append(skill)
                else:
                    tools.append(skill)
                break

    concept_signals = {
        "api": "REST API design",
        "microservice": "microservices",
        "authentication": "authentication",
        "authorization": "authorization",
        "ci/cd": "CI/CD",
        "cicd": "CI/CD",
        "database": "database design",
        "orm": "ORM",
        "testing": "testing",
        "agile": "agile",
        "scrum": "scrum",
    }
    for signal, label in concept_signals.items():
        if signal in jd_lower:
            concepts.append(label)

    soft_signals = {
        "communication": "communication",
        "teamwork": "teamwork",
        "leadership": "leadership",
        "problem solving": "problem solving",
        "analytical": "analytical",
        "detail oriented": "detail-oriented",
        "self motivated": "self-motivated",
    }
    for signal, label in soft_signals.items():
        if signal in jd_lower:
            soft_skills.append(label)

    return {
        "must_have": list(set(must_have)),
        "nice_to_have": list(set(nice_to_have)),
        "tools": list(set(tools)),
        "concepts": list(set(concepts)),
        "soft_skills": list(set(soft_skills)),
    }
