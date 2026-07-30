import logging
import httpx

logger = logging.getLogger(__name__)

TECH_KEYWORDS = [
    "python", "django", "fastapi", "flask", "react", "vue", "angular",
    "node.js", "nodejs", "typescript", "javascript", "postgresql", "mysql",
    "mongodb", "redis", "docker", "kubernetes", "aws", "gcp", "azure",
    "terraform", "jenkins", "github actions", "ci/cd", "graphql", "grpc",
    "microservices", "kafka", "rabbitmq", "celery", "nginx", "apache",
    "linux", "git", "sql", "nosql", "elasticsearch", "selenium",
    "machine learning", "deep learning", "ai", "llm", "nlp",
]

SIZE_SIGNALS = {
    "startup": ["startup", "series a", "series b", "series c", "seed", "early stage", "small team"],
    "mid-size": ["mid-size", "midsize", "growing", "scaling", "200 employees", "500 employees"],
    "enterprise": ["enterprise", "fortune", "multinational", "global", "consulting", "mnc", "1000+ employees"],
}

INDUSTRY_SIGNALS = {
    "fintech": ["fintech", "banking", "finance", "payment", "insurance", "neobank"],
    "healthtech": ["healthtech", "healthcare", "medical", "clinical", "hospital"],
    "edtech": ["edtech", "education", "learning", "student", "school"],
    "ecommerce": ["ecommerce", "e-commerce", "marketplace", "retail", "shopping"],
    "saas": ["saas", "platform", "software as a service", "subscription"],
    "ai": ["artificial intelligence", "machine learning", "ai", "deep learning", "nlp"],
}


def scrape_company_context(company_name: str = "", apply_url: str = None) -> dict:
    result = {
        "description": "",
        "tech_stack": [],
        "size": "",
        "industry": "",
    }

    url = None
    if apply_url:
        from urllib.parse import urlparse
        parsed = urlparse(apply_url)
        url = f"{parsed.scheme}://{parsed.netloc}"

    if not url and company_name:
        url = f"https://www.{company_name.lower().replace(' ', '')}.com"

    if not url:
        return result

    try:
        response = httpx.get(url, timeout=5.0, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; JobbLoot/1.0)"
        })
        if response.status_code != 200:
            return result

        text = response.text.lower()

        meta_desc = ""
        if '<meta name="description"' in text:
            import re
            match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', text, re.IGNORECASE)
            if match:
                meta_desc = match.group(1)
        result["description"] = meta_desc[:200]

        for tech in TECH_KEYWORDS:
            if tech in text:
                result["tech_stack"].append(tech.title())

        for size, signals in SIZE_SIGNALS.items():
            if any(s in text for s in signals):
                result["size"] = size
                break

        for industry, signals in INDUSTRY_SIGNALS.items():
            if any(s in text for s in signals):
                result["industry"] = industry
                break

    except Exception as e:
        logger.warning(f"Company scrape failed for {company_name}: {e}")

    return result
