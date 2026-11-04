"""Unit and security tests for SSRF protection and safe source retrieval."""

import pytest

from app.core.exceptions import SSRFSecurityError
from app.services.source_retrieval import SourceRetrievalService


def test_ssrf_blocks_invalid_schemes() -> None:
    """Verify non-HTTP(S) schemes raise SSRFSecurityError."""
    retriever = SourceRetrievalService()
    with pytest.raises(SSRFSecurityError, match="Disallowed URL scheme"):
        retriever.validate_url_safety("file:///etc/passwd")

    with pytest.raises(SSRFSecurityError, match="Disallowed URL scheme"):
        retriever.validate_url_safety("ftp://example.com/file.txt")

    with pytest.raises(SSRFSecurityError, match="Disallowed URL scheme"):
        retriever.validate_url_safety("gopher://127.0.0.1:70")


def test_ssrf_blocks_localhost_and_internal_hostnames() -> None:
    """Verify localhost, .local, and .internal destinations are rejected."""
    retriever = SourceRetrievalService()
    with pytest.raises(SSRFSecurityError, match="access to local destinations is prohibited"):
        retriever.validate_url_safety("http://localhost:8080/admin")

    with pytest.raises(SSRFSecurityError, match="access to local destinations is prohibited"):
        retriever.validate_url_safety("http://service.local/api")

    with pytest.raises(SSRFSecurityError, match="access to local destinations is prohibited"):
        retriever.validate_url_safety("https://db.internal/metrics")


def test_ssrf_blocks_loopback_and_private_ips() -> None:
    """Verify private and loopback IP addresses raise SSRFSecurityError."""
    retriever = SourceRetrievalService()

    with pytest.raises(SSRFSecurityError, match="Disallowed IP destination"):
        retriever.validate_url_safety("http://127.0.0.1:8000")

    with pytest.raises(SSRFSecurityError, match="Disallowed IP destination"):
        retriever.validate_url_safety("http://10.0.0.5/secret")

    with pytest.raises(SSRFSecurityError, match="Disallowed IP destination"):
        retriever.validate_url_safety("http://192.168.1.1/router")

    with pytest.raises(SSRFSecurityError, match="Disallowed IP destination"):
        retriever.validate_url_safety("http://172.16.0.1/internal")


def test_ssrf_blocks_cloud_metadata_ips() -> None:
    """Verify AWS/GCP cloud metadata IP 169.254.169.254 is blocked."""
    retriever = SourceRetrievalService()
    with pytest.raises(SSRFSecurityError, match="Disallowed IP destination"):
        retriever.validate_url_safety("http://169.254.169.254/latest/meta-data")


@pytest.mark.asyncio
async def test_fetch_source_catches_ssrf_gracefully() -> None:
    """Verify fetch_source returns an inaccessible RetrievedSource object without crashing."""
    retriever = SourceRetrievalService()
    result = await retriever.fetch_source("http://127.0.0.1:9999/status")

    assert result.is_accessible is False
    assert result.status_code == 0
    assert result.error is not None
    assert "SSRF violation" in result.error

