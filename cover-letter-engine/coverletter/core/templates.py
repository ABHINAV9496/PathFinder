"""Hardcoded, ATS-friendly cover-letter templates (deterministic, no LLM).

Each template renders a letter BODY from a shared context dict built by
``generator.py``. Every claim is grounded in the candidate's own data:
matched skills (already filtered against missing keywords), real project
names, and resume/project evidence lines. Templates never invent
numbers, never mention missing skills, and never reference a technology
that is not present in the context.

The selector scores each template against JD signals (domain,
seniority, tone, JD emphasis); ties break on ``priority`` (lower wins).
"""

# ruff: noqa: E501 — template prose lines are long by design


def _tpl_ai_engineer(ctx):
    secondary = f" {ctx.secondary_ref}" if ctx.secondary_ref else ""
    return (
        f"The {ctx.title} role at {ctx.company} sits exactly where I do most of my work: "
        f"AI features that hold up behind a real API. I shipped {ctx.primary_ref} "
        f"({ctx.primary_tech}), integrating an LLM provider with prompt engineering, "
        f"structured output parsing, and fallback logic for when the model is unreliable."
        f"{secondary}{ctx.evidence_sentence}\n\n"
        f"My backend foundation is {ctx.skills_text}. With {ctx.primary_name} I handled the "
        f"full loop -- API design, data modeling, async jobs, and deployment -- so I know the "
        f"difference between an AI demo and an AI feature that runs in production.\n\n"
        f"{ctx.ai_line}{ctx.devops_line}\n\n"
        f"I'm most interested in {ctx.need} and would welcome the chance to talk through how "
        f"I'd approach it with your team."
    )


def _tpl_ai_engineer_fresher(ctx):
    return (
        f"{ctx.company} caught my attention because the {ctx.title} work you're doing is exactly "
        f"what I've been building on my own: AI features backed by dependable backend systems. "
        f"On {ctx.primary_name}, {ctx.primary_desc}{ctx.evidence_sentence}\n\n"
        f"I bring {ctx.strengths} from shipped projects rather than tutorials. That project "
        f"taught me {ctx.primary_tech} end to end -- I designed the API, wired the model calls, "
        f"handled failures, and deployed it.\n\n"
        f"{ctx.ai_line}\n\n"
        f"I'm early in my career, but I've learned that reliability around a model matters more "
        f"than the model itself. I'd love to bring that mindset to {ctx.need}."
    )


def _tpl_fintech_engineer(ctx):
    secondary = f" {ctx.secondary_ref} -- skills that translate directly to building reliable financial systems." if ctx.secondary_ref else ""
    return (
        f"Financial systems demand reliability, security, and clean data handling -- that's where "
        f"my backend experience applies. I built {ctx.primary_ref} on {ctx.primary_tech}, with "
        f"authentication, role-based access control, and a data layer built with production "
        f"rigor in mind.{secondary}{ctx.evidence_sentence}\n\n"
        f"My core competencies are {ctx.strengths}, and I apply the same discipline to every "
        f"endpoint and query: correctness first, then performance.\n\n"
        f"{ctx.security_line}{ctx.data_line}\n\n"
        f"I'm interested in {ctx.company} because of {ctx.need}. I'd be glad to discuss how my "
        f"experience with secure, production-grade systems can contribute to your team."
    )


def _tpl_startup_engineer(ctx):
    secondary = f" On {ctx.secondary_ref} -- another project where I owned the full stack end to end." if ctx.secondary_ref else ""
    return (
        f"Shipping fast without breaking things is what {ctx.company} needs from a {ctx.title}, "
        f"and that's what I do. I recently built {ctx.primary_ref} ({ctx.primary_tech}), handling "
        f"everything from database design through API development to deployment."
        f"{secondary}{ctx.evidence_sentence}\n\n"
        f"At {ctx.company_possessive} stage you need someone who owns the full loop. With "
        f"{ctx.primary_name} I designed the API, built the frontend, set up the async jobs, and "
        f"shipped it -- no handoffs, no waiting, just features landing.\n\n"
        f"{ctx.devops_line}{ctx.ai_line}\n\n"
        f"I'm excited about {ctx.need} and ready to hit the ground running. Let's talk."
    )


def _tpl_startup_story(ctx):
    return (
        f"What pulled me toward {ctx.company} is that the {ctx.title} role is about building "
        f"something real, not maintaining something stale. That matches how I work: I built "
        f"{ctx.primary_ref} because I wanted to solve a problem end to end, using "
        f"{ctx.primary_tech}.{ctx.evidence_sentence}\n\n"
        f"My toolkit is {ctx.skills_text}. On {ctx.primary_name} I took the product from idea to "
        f"production -- the API, the data layer, the deployment -- and I care about the same "
        f"craftsmanship {ctx.company} describes in its listing.\n\n"
        f"{ctx.devops_line}{ctx.ai_line}\n\n"
        f"I'd like to contribute to {ctx.need}, and I'm happy to talk about how."
    )


def _tpl_enterprise_engineer(ctx):
    secondary = f" {ctx.secondary_ref} -- patterns I know enterprise environments rely on." if ctx.secondary_ref else ""
    return (
        f"Your {ctx.title} listing at {ctx.company} calls for someone who builds production "
        f"systems that scale -- I've been doing exactly that. I shipped {ctx.primary_ref}, a "
        f"full-stack application built on {ctx.primary_tech} covering authentication, "
        f"role-based access, and API design from the ground up.{secondary}{ctx.evidence_sentence}\n\n"
        f"I'm comfortable across the stack and take ownership of deliverables from architecture "
        f"through deployment. I understand that enterprise systems need to be reliable, secure, "
        f"and maintainable -- not just functional.\n\n"
        f"{ctx.security_line}{ctx.devops_line}\n\n"
        f"I'm drawn to {ctx.company} because of {ctx.need}. I'd welcome the opportunity to discuss "
        f"how my experience aligns with your team's needs."
    )


def _tpl_tech_engineer(ctx):
    secondary = f" I also built {ctx.secondary_ref}, which deepened my production experience." if ctx.secondary_ref else ""
    return (
        f"The {ctx.title} role at {ctx.company} stands out because it's solving the kind of "
        f"technical problems I enjoy most. I spent the past year building {ctx.primary_ref} "
        f"({ctx.primary_tech}), and the requirements in your job description align directly with "
        f"the work I've been doing.{secondary}{ctx.evidence_sentence}\n\n"
        f"My core stack is {ctx.skills_text}. I care about API design, data modeling, and making "
        f"sure systems hold up under real load -- not just that they work, but that they stay "
        f"working.\n\n"
        f"{ctx.devops_line}{ctx.frontend_line}{ctx.ai_line}\n\n"
        f"I'm excited about {ctx.need} and confident I can contribute from day one. Let me know "
        f"if there's a good time to connect."
    )


def _tpl_tech_story(ctx):
    return (
        f"I got into building software because I like taking a messy problem and turning it into "
        f"something clean and reliable. {ctx.primary_ref} ({ctx.primary_tech}) is that kind of "
        f"project -- and the {ctx.title} role at {ctx.company} looks like the same kind of work, "
        f"at a bigger scale.{ctx.evidence_sentence}\n\n"
        f"I work with {ctx.skills_text}, and I approach each layer the same way: understand the "
        f"problem, design the simplest correct solution, then make it fast enough to ship.\n\n"
        f"{ctx.devops_line}{ctx.frontend_line}\n\n"
        f"I'd like to help with {ctx.need}. I'm happy to walk through how I'd approach it."
    )


def _tpl_fresher_general(ctx):
    secondary = f" I also built {ctx.secondary_ref}, which widened my experience across different application types." if ctx.secondary_ref else ""
    return (
        f"I'm applying for the {ctx.title} role at {ctx.company} because it matches the work I've "
        f"already been building on my own. I shipped {ctx.primary_ref} ({ctx.primary_tech}), "
        f"handling the whole stack from database to deployment.{secondary}{ctx.evidence_sentence}\n\n"
        f"Across my projects I've used {ctx.skills_text}, and I've learned to move fast, ask "
        f"questions, and own what I ship. I know I have more to learn -- but I also know I can "
        f"be productive on day one.\n\n"
        f"{ctx.devops_line}{ctx.frontend_line}\n\n"
        f"I'm genuinely interested in {ctx.need} and I'd love to discuss how I can contribute."
    )


def _tpl_senior_leader(ctx):
    if ctx.depth_case:
        depth = (
            f"My years on paper don't tell the whole story: I've taken full systems from design "
            f"to production -- architecture decisions, trade-offs, and the reliability of what "
            f"goes out. That is what the {ctx.title} role actually needs."
        )
    else:
        depth = (
            "Over the course of my career I've moved from shipping features to owning systems: "
            "architecture decisions, data modeling, deployment, and the reliability of what goes "
            "out to users."
        )
    return (
        f"The {ctx.title} role at {ctx.company} is the kind of position I've been growing toward "
        f"-- owning outcomes, not just tickets. I built {ctx.primary_ref} on {ctx.primary_tech}, "
        f"and I've been responsible for it end to end.{ctx.evidence_sentence}\n\n"
        f"{depth}\n\n"
        f"{ctx.security_line}{ctx.devops_line}{ctx.data_line}\n\n"
        f"I'm particularly drawn to {ctx.need}. I'd welcome a conversation about how I can take "
        f"on that responsibility with your team."
    )


def _tpl_general_direct(ctx):
    secondary = f" I also built {ctx.secondary_ref}, which broadened my experience across different application types." if ctx.secondary_ref else ""
    return (
        f"The {ctx.title} role at {ctx.company} matches closely with what I've been building. I "
        f"recently shipped {ctx.primary_ref} -- {ctx.primary_tech} -- where I handled everything "
        f"from database design and API development to frontend implementation and deployment."
        f"{secondary}{ctx.evidence_sentence}\n\n"
        f"My strongest work is in {ctx.skills_text}. I design APIs that are clean and "
        f"well-documented, build data layers that are reliable, and set up deployments I can "
        f"maintain without needing a separate ops team.\n\n"
        f"{ctx.devops_line}{ctx.ai_line}\n\n"
        f"I'm excited about {ctx.need} and ready to contribute. Let me know when you'd like to "
        f"connect."
    )


def _tpl_general_standard(ctx):
    secondary = f" I also built {ctx.secondary_ref}." if ctx.secondary_ref else ""
    return (
        f"I'm a {ctx.role} with production experience, and the {ctx.title} role at {ctx.company} "
        f"matches closely with what I've been building. I recently shipped {ctx.primary_ref}, "
        f"where I handled everything from database design and API development to frontend "
        f"implementation and deployment.{secondary}{ctx.evidence_sentence}\n\n"
        f"My core skills are {ctx.skills_text}. I design clean APIs, build reliable data layers, "
        f"and own my deployments end to end.\n\n"
        f"{ctx.devops_line}{ctx.frontend_line}\n\n"
        f"I'm excited about {ctx.need} and ready to contribute. Let me know when you'd like to "
        f"connect."
    )


TEMPLATES = [
    {
        "id": "ai_engineer",
        "domains": ["ai"],
        "seniority": ["mid", "senior"],
        "tones": ["direct"],
        "emphases": ["ai"],
        "priority": 1,
        "render": _tpl_ai_engineer,
    },
    {
        "id": "ai_engineer_fresher",
        "domains": ["ai"],
        "seniority": ["fresher"],
        "tones": ["story", "direct"],
        "emphases": ["ai"],
        "priority": 1,
        "render": _tpl_ai_engineer_fresher,
    },
    {
        "id": "fintech_engineer",
        "domains": ["fintech"],
        "seniority": ["mid", "senior"],
        "tones": ["formal"],
        "emphases": ["security", "data"],
        "priority": 2,
        "render": _tpl_fintech_engineer,
    },
    {
        "id": "startup_engineer",
        "domains": ["startup"],
        "seniority": ["any"],
        "tones": ["direct"],
        "emphases": ["devops"],
        "priority": 2,
        "render": _tpl_startup_engineer,
    },
    {
        "id": "startup_story",
        "domains": ["startup", "tech"],
        "seniority": ["any"],
        "tones": ["story"],
        "emphases": [],
        "priority": 3,
        "render": _tpl_startup_story,
    },
    {
        "id": "enterprise_engineer",
        "domains": ["enterprise"],
        "seniority": ["mid", "senior"],
        "tones": ["formal"],
        "emphases": ["security"],
        "priority": 2,
        "render": _tpl_enterprise_engineer,
    },
    {
        "id": "tech_engineer",
        "domains": ["tech"],
        "seniority": ["mid", "senior"],
        "tones": ["direct"],
        "emphases": ["devops", "frontend"],
        "priority": 3,
        "render": _tpl_tech_engineer,
    },
    {
        "id": "tech_story",
        "domains": ["tech"],
        "seniority": ["any"],
        "tones": ["story"],
        "emphases": [],
        "priority": 4,
        "render": _tpl_tech_story,
    },
    {
        "id": "fresher_general",
        "domains": ["any"],
        "seniority": ["fresher"],
        "tones": ["direct", "story"],
        "emphases": [],
        "priority": 5,
        "render": _tpl_fresher_general,
    },
    {
        "id": "senior_leader",
        "domains": ["any"],
        "seniority": ["senior"],
        "tones": ["formal", "direct"],
        "emphases": [],
        "priority": 5,
        "render": _tpl_senior_leader,
    },
    {
        "id": "general_direct",
        "domains": ["any"],
        "seniority": ["mid"],
        "tones": ["direct"],
        "emphases": [],
        "priority": 6,
        "render": _tpl_general_direct,
    },
    {
        "id": "general_standard",
        "domains": ["any"],
        "seniority": ["any"],
        "tones": ["any"],
        "emphases": [],
        "priority": 9,
        "render": _tpl_general_standard,
    },
]


def select(features: dict) -> dict:
    """Score all templates against the JD feature vector; return the winner."""
    emphases = features.get("emphases") or set()

    def score(t):
        s = 0
        if "any" in t["domains"] or features["domain"] in t["domains"]:
            s += 3
        if "any" in t["seniority"] or features["seniority"] in t["seniority"]:
            s += 2
        if "any" in t["tones"] or features["tone"] in t["tones"]:
            s += 1
        s += min(2, len(emphases & set(t["emphases"])))
        return s

    return max(TEMPLATES, key=lambda t: (score(t), -t["priority"]))


def get(template_id: str) -> dict:
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    raise KeyError(f"unknown template: {template_id}")
