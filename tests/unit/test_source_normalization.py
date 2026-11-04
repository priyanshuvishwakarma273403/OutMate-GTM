"""Unit tests for URL normalization, deduplication, and source classification."""

from app.domain.models.evidence import EvidenceSourceType
from app.services.source_normalization import (
    classify_source_type,
    deduplicate_urls,
    extract_domain_from_url,
    normalize_url,
)


def test_normalize_url_strips_tracking_params_and_fragments() -> None:
    """Verify UTM parameters, fbclid, and fragments are removed."""
    dirty_url = (
        "https://example.com/about/?utm_source=google&utm_medium=cpc"
        "&utm_campaign=brand&fbclid=IwAR123&keep=true#leadership"
    )
    normalized = normalize_url(dirty_url)
    assert normalized == "https://example.com/about?keep=true"


def test_normalize_url_cleans_trailing_slashes_and_default_ports() -> None:
    """Verify redundant slashes and default ports 80/443 are normalized."""
    url = "https://example.com:443/company/overview///"
    normalized = normalize_url(url)
    assert normalized == "https://example.com/company/overview"


def test_deduplicate_urls_preserves_order() -> None:
    """Verify URL list is deduplicated while retaining ranking."""
    urls = [
        "https://vercel.com/about",
        "https://vercel.com/about?utm_source=twitter",
        "https://techcrunch.com/article",
        "https://vercel.com/about/",
        "https://forbes.com/vercel-profile",
    ]
    deduped = deduplicate_urls(urls)
    assert deduped == [
        "https://vercel.com/about",
        "https://techcrunch.com/article",
        "https://forbes.com/vercel-profile",
    ]


def test_extract_domain_from_url() -> None:
    """Verify domain extraction strips www, ports, and paths."""
    assert extract_domain_from_url("https://www.vercel.com/pricing") == "vercel.com"
    assert extract_domain_from_url("http://sub.domain.co.uk:8080/test") == "sub.domain.co.uk"
    assert extract_domain_from_url("invalid-url") == ""


def test_classify_source_type_official_website() -> None:
    """Verify official domain URLs are classified as OFFICIAL_WEBSITE or PRESS_RELEASE."""
    assert (
        classify_source_type("https://vercel.com/about", "vercel.com")
        == EvidenceSourceType.OFFICIAL_WEBSITE
    )
    assert (
        classify_source_type("https://vercel.com/press/announcement-2024", "vercel.com")
        == EvidenceSourceType.PRESS_RELEASE
    )


def test_classify_source_type_news_and_registries() -> None:
    """Verify news outlets and registries are classified accurately."""
    assert (
        classify_source_type("https://techcrunch.com/2024/01/01/startup-news", "vercel.com")
        == EvidenceSourceType.NEWS_ARTICLE
    )
    assert (
        classify_source_type("https://www.sec.gov/edgar/browse/?CIK=123", "vercel.com")
        == EvidenceSourceType.PUBLIC_REGISTRY
    )
    assert (
        classify_source_type("https://randomblog.org/post", "vercel.com")
        == EvidenceSourceType.OTHER
    )

