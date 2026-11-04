"""Unit tests for company identity resolution service."""

import pytest

from app.integrations.search.base import SearchResultItem
from app.integrations.search.providers.mock import MockSearchClient
from app.services.company_identity import (
    CompanyIdentityResolutionService,
    IdentityResolutionStatus,
)


def test_normalize_company_name_removes_legal_suffixes() -> None:
    """Verify legal suffixes such as Inc, LLC, Corp, Ltd are stripped cleanly."""
    service = CompanyIdentityResolutionService(search_client=MockSearchClient())
    assert service.normalize_company_name("Vercel, Inc.") == "Vercel"
    assert service.normalize_company_name("Acme Corporation") == "Acme"
    assert service.normalize_company_name("Global Technologies LLC") == "Global Technologies"
    assert service.normalize_company_name("Stripe Ltd.") == "Stripe"


def test_clean_domain_normalization() -> None:
    """Verify raw domain strings with protocols, www, or paths are cleaned."""
    service = CompanyIdentityResolutionService(search_client=MockSearchClient())
    assert service.clean_domain("https://www.vercel.com/about") == "vercel.com"
    assert service.clean_domain("stripe.com/") == "stripe.com"
    assert service.clean_domain("invalid") is None
    assert service.clean_domain(None) is None


@pytest.mark.asyncio
async def test_resolve_identity_with_user_supplied_domain() -> None:
    """Verify user supplied domain is immediately accepted as canonical."""
    service = CompanyIdentityResolutionService(search_client=MockSearchClient())
    resolution = await service.resolve_identity("Vercel", "https://vercel.com/")

    assert resolution.status == IdentityResolutionStatus.RESOLVED
    assert resolution.resolved_domain == "vercel.com"
    assert resolution.official_website_url == "https://vercel.com"
    assert resolution.confidence >= 0.95


@pytest.mark.asyncio
async def test_resolve_identity_via_search_discovery() -> None:
    """Verify official domain is discovered from search results when matching company token."""
    mock_results = [
        SearchResultItem(
            url="https://en.wikipedia.org/wiki/Vercel",
            title="Vercel - Wikipedia",
            snippet="Vercel is a cloud platform company.",
            score=0.9,
        ),
        SearchResultItem(
            url="https://vercel.com",
            title="Vercel: Build and deploy the best Web experiences",
            snippet="Vercel frontend cloud platform.",
            score=0.98,
        ),
    ]
    mock_client = MockSearchClient(predefined_results=mock_results)
    service = CompanyIdentityResolutionService(search_client=mock_client)

    resolution = await service.resolve_identity("Vercel Inc")
    assert resolution.status == IdentityResolutionStatus.RESOLVED
    assert resolution.resolved_domain == "vercel.com"
    assert resolution.confidence >= 0.90


@pytest.mark.asyncio
async def test_resolve_identity_detects_ambiguity() -> None:
    """Verify ambiguity status is assigned when multiple distinct companies share name."""
    mock_results = [
        SearchResultItem(
            url="https://apex.com",
            title="Apex Global Systems",
            snippet="Apex enterprise cloud tools.",
            score=0.9,
        ),
        SearchResultItem(
            url="https://apexhosting.com",
            title="Apex Hosting - Game Servers",
            snippet="Apex minecraft server hosting.",
            score=0.88,
        ),
    ]
    mock_client = MockSearchClient(predefined_results=mock_results)
    service = CompanyIdentityResolutionService(search_client=mock_client)

    resolution = await service.resolve_identity("Apex")
    assert resolution.status == IdentityResolutionStatus.AMBIGUOUS
    assert resolution.resolved_domain == "apex.com"
    assert len(resolution.candidate_domains) >= 2
    assert "apexhosting.com" in resolution.candidate_domains


@pytest.mark.asyncio
async def test_resolve_identity_unresolved_when_no_match() -> None:
    """Verify UNRESOLVED status when no candidate domains match the company name."""
    mock_results = [
        SearchResultItem(
            url="https://unrelated-domain.com",
            title="Unrelated Topic",
            snippet="Completely unrelated content.",
            score=0.3,
        )
    ]
    mock_client = MockSearchClient(predefined_results=mock_results)
    service = CompanyIdentityResolutionService(search_client=mock_client)

    resolution = await service.resolve_identity("NonExistentCorpXYZ123")
    assert resolution.status == IdentityResolutionStatus.UNRESOLVED
    assert resolution.confidence < 0.5

