import hashlib
import re

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

JUNK_DOMAINS = {
    "sentry.io", "wixpress.com", "example.com", "test.com",
    "squarespace.com", "wix.com", "godaddy.com", "googleapis.com",
    "cloudflare.com", "github.io", "herokuapp.com", "vercel.app",
    "netlify.app", "apple.com", "google.com", "microsoft.com",
    "amazonaws.com", "facebook.com", "meta.com", "samsung.com",
    "oracle.com", "ibm.com", "adobe.com", "salesforce.com",
    "vmware.com", "cognizant.com", "capgemini.com", "infosys.com",
    "wipro.com", "tcs.com", "techmahindra.com", "hcl.com",
    "accenture.com", "deloitte.com", "ey.com", "pwc.com",
    "kpmg.com", "mba.com", "no-reply", "donotreply",
    "mailer-daemon", "postmaster", "noreply",
}

SPAM_DOMAINS = [
    "linkedin.com", "indeed.com", "glassdoor.com", "naukri.com",
    "monster.com", "shine.com", "timesjobs.com", "foundit.in",
    "cutshort.io", "hirist.com", "instahyre.com", "cutshort.in",
    "wellfound.com", "angel.co", "ycombinator.com",
]


def is_company_email(email: str) -> tuple:
    """Validates whether an email is likely a real company email."""
    if not email or not isinstance(email, str):
        return False, "empty"

    email = email.strip().lower()

    if not EMAIL_REGEX.match(email):
        return False, "invalid format"

    domain = email.split("@")[-1]

    if domain in JUNK_DOMAINS:
        return False, f"junk domain: {domain}"

    if any(sd in domain for sd in SPAM_DOMAINS):
        return False, f"job board domain: {domain}"

    return True, "valid"


def make_uid(title: str, company: str, location: str = "") -> str:
    """Generate a unique ID for deduplication based on title + company + location."""
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{location.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def _normalize(text: str) -> str:
    """Normalize text for fuzzy matching: lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[\(\)\[\]\{\},./\\:;!?\"']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Remove common filler words that vary across sources
    _fillers = {"remote", "hybrid", "onsite", "on-site", "fulltime", "full-time", "wfh", "india", "bangalore", "bengaluru"}
    words = [w for w in text.split() if w not in _fillers]
    return " ".join(words)


def _title_tokens(title: str) -> set[str]:
    """Extract meaningful tokens from a job title for fuzzy matching."""
    normed = _normalize(title)
    # Remove common role suffixes/prefixes
    _noise = {"developer", "engineer", "sr", "jr", "senior", "junior", "lead", "staff", "principal", "intern"}
    tokens = set(normed.split())
    return tokens - _noise


def jobs_are_same(a: dict, b: dict) -> bool:
    """Fuzzy check if two job dicts represent the same job posting."""
    norm_a = _normalize(a.get("company", ""))
    norm_b = _normalize(b.get("company", ""))
    if not norm_a or not norm_b:
        return False

    # Company must be reasonably similar (>= 80% overlap)
    comp_a = set(norm_a.split())
    comp_b = set(norm_b.split())
    if comp_a and comp_b:
        comp_overlap = len(comp_a & comp_b) / max(len(comp_a | comp_b), 1)
        if comp_overlap < 0.6:
            return False

    # Title overlap must be high (>= 70% of tokens match)
    tok_a = _title_tokens(a.get("title", ""))
    tok_b = _title_tokens(b.get("title", ""))
    if tok_a and tok_b:
        title_overlap = len(tok_a & tok_b) / max(min(len(tok_a), len(tok_b)), 1)
        if title_overlap < 0.6:
            return False
    elif not tok_a and not tok_b:
        pass  # both empty titles — let company match decide
    else:
        return False

    return True


def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """Deduplicate jobs using fuzzy matching. Keeps the version with more data."""
    if not jobs:
        return []

    unique = []
    for job in jobs:
        is_dup = False
        for i, existing in enumerate(unique):
            if jobs_are_same(job, existing):
                # Keep the version with more data (longer description, has salary, etc.)
                score_new = len(job.get("description", "")) + (1000 if job.get("salary") else 0)
                score_existing = len(existing.get("description", "")) + (1000 if existing.get("salary") else 0)
                if score_new > score_existing:
                    unique[i] = job
                is_dup = True
                break
        if not is_dup:
            unique.append(job)

    return unique


def clean_html(html_text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not html_text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', html_text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def html_to_markdown(html_text: str) -> str:
    """Convert HTML to markdown, preserving formatting."""
    if not html_text:
        return ""
    if "<" not in html_text:
        return html_text.strip()

    text = html_text

    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?p[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?div[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?li[^>]*>', '\n- ', text, flags=re.IGNORECASE)
    text = re.sub(r'</?[ou]l[^>]*>', '\n', text, flags=re.IGNORECASE)

    text = re.sub(r'<a\s+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.IGNORECASE)
    text = re.sub(r'</?b[^>]*>', '**', text, flags=re.IGNORECASE)
    text = re.sub(r'</?strong[^>]*>', '**', text, flags=re.IGNORECASE)
    text = re.sub(r'</?i[^>]*>', '*', text, flags=re.IGNORECASE)
    text = re.sub(r'</?em[^>]*>', '*', text, flags=re.IGNORECASE)

    text = re.sub(r'<[^>]+>', '', text)

    import html as html_mod
    text = html_mod.unescape(text)

    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[^\S\n]+', ' ', text)
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    text = _collapse_list_items(text)
    return text.strip()


def _collapse_list_items(text: str) -> str:
    """Collapse blank lines between consecutive list items and remove empty list items."""
    lines = text.split('\n')
    result = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        is_list_item = stripped.startswith('- ') or re.match(r'^\d+\.\s', stripped)
        is_empty_bullet = stripped == '-' or stripped == '- ' or re.match(r'^\d+\.\s*$', stripped)
        if is_empty_bullet:
            continue
        if is_list_item:
            in_list = True
            result.append(line)
        elif in_list and stripped == '':
            continue
        elif in_list and stripped != '' and not is_list_item:
            in_list = False
            result.append(line)
        else:
            result.append(line)
    return '\n'.join(result)


def safe_console(text: str) -> str:
    """Make text safe for Windows console output."""
    try:
        return str(text).encode('utf-8', errors='replace').decode('utf-8')
    except Exception:
        return str(text)
