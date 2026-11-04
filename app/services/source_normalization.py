"""URL normalization and source categorization utilities."""

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.domain.models.evidence import EvidenceSourceType

TRACKING_PARAM_PREFIXES = ("utm_",)
TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "ref",
    "source",
    "mc_eid",
    "msclkid",
    "yclid",
    "_hsenc",
    "_hsmi",
}


def normalize_url(url: str) -> str:
    """Normalize a URL by stripping tracking parameters, fragments, and redundant slashes."""
    if not url or not isinstance(url, str):
        return ""

    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove standard port specifications
    if (scheme == "http" and netloc.endswith(":80")) or (
        scheme == "https" and netloc.endswith(":443")
    ):
        netloc = netloc.rsplit(":", 1)[0]

    # Clean path
    path = parsed.path or "/"
    # Collapse duplicate slashes
    path = re.sub(r"/+", "/", path)
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    # Filter tracking query parameters
    query_tuples = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        k_lower = k.lower()
        if k_lower in TRACKING_PARAMS or any(
            k_lower.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES
        ):
            continue
        query_tuples.append((k, v))

    clean_query = urlencode(query_tuples) if query_tuples else ""

    # Clear fragment
    return urlunparse((scheme, netloc, path, parsed.params, clean_query, ""))


def deduplicate_urls(urls: list[str]) -> list[str]:
    """Deduplicate a list of URLs while preserving their initial relative ranking."""
    seen: set[str] = set()
    result: list[str] = []
    for u in urls:
        norm = normalize_url(u)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def extract_domain_from_url(url: str) -> str:
    """Extract clean domain name (e.g., 'vercel.com') from URL."""
    try:
        parsed = urlparse(url.strip())
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc.split(":")[0]
    except Exception:
        return ""


def classify_source_type(url: str, target_domain: str, title: str = "") -> EvidenceSourceType:
    """Categorize evidence source origin based on URL, domain, and title indicators."""
    source_domain = extract_domain_from_url(url)
    clean_target = extract_domain_from_url(f"https://{target_domain}") if target_domain else ""

    # 1. Official First-Party Website
    if clean_target and (
        source_domain == clean_target or source_domain.endswith(f".{clean_target}")
    ):
        path = urlparse(url).path.lower()
        if any(term in path for term in ("press", "newsroom", "announcement", "pr")):
            return EvidenceSourceType.PRESS_RELEASE
        return EvidenceSourceType.OFFICIAL_WEBSITE

    # 2. Regulatory & Government Registries
    if any(
        reg in source_domain
        for reg in ("sec.gov", "companieshouse.gov.uk", "opencorporates.com", "edgar-online.com")
    ):
        return EvidenceSourceType.PUBLIC_REGISTRY

    # 3. Major Press & Tech News Publications
    news_domains = (
        "techcrunch.com",
        "forbes.com",
        "bloomberg.com",
        "reuters.com",
        "venturebeat.com",
        "wsj.com",
        "theverge.com",
        "cnbc.com",
        "businessinsider.com",
        "zdnet.com",
    )
    if any(news in source_domain for news in news_domains):
        return EvidenceSourceType.NEWS_ARTICLE

    # 4. Job Postings
    if any(j in source_domain for j in ("greenhouse.io", "lever.co", "workable.com")):
        return EvidenceSourceType.JOB_POSTING

    title_lower = title.lower()
    if "press release" in title_lower or "pr newswire" in title_lower:
        return EvidenceSourceType.PRESS_RELEASE

    return EvidenceSourceType.OTHER
