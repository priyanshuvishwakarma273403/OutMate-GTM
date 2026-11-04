"""Source retrieval service with robust SSRF protection and safe streaming."""

import ipaddress
import socket
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, Field

from app.core.exceptions import SSRFSecurityError
from app.core.logging import get_logger

logger = get_logger("services.source_retrieval")


class RetrievedSource(BaseModel):
    """Raw content and metadata retrieved from an external webpage."""

    url: str = Field(..., description="Canonical or requested URL")
    final_url: str = Field(..., description="Final URL after following redirects")
    status_code: int = Field(default=0, description="HTTP status code")
    raw_html: str = Field(default="", description="Extracted HTML content")
    content_type: str = Field(default="", description="MIME content type")
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when source was retrieved",
    )
    is_accessible: bool = Field(default=False, description="True if HTTP 200 and within limits")
    error: str | None = Field(default=None, description="Error reason if inaccessible")


class SourceRetrievalService:
    """Safe, SSRF-protected HTTP retrieval engine for public web sources."""

    ALLOWED_SCHEMES = {"http", "https"}
    ALLOWED_CONTENT_TYPES = {
        "text/html",
        "application/xhtml+xml",
        "text/plain",
    }
    MAX_BODY_BYTES = 2 * 1024 * 1024  # 2 Megabytes limit
    MAX_REDIRECTS = 3
    DEFAULT_TIMEOUT = 10.0

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.timeout = timeout
        self._custom_client = http_client

    def validate_url_safety(self, url: str) -> None:
        """Validate URL to prevent SSRF, DNS rebinding, and private IP destination attacks."""
        if not url or not isinstance(url, str):
            raise SSRFSecurityError("Invalid URL: must be a non-empty string")

        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        if scheme not in self.ALLOWED_SCHEMES:
            raise SSRFSecurityError(
                f"Disallowed URL scheme '{scheme}'. Only HTTP and HTTPS are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise SSRFSecurityError(f"Invalid URL '{url}': hostname is missing")

        hostname_lower = hostname.lower()

        # Block localhost variants and internal reserved names
        if (
            hostname_lower == "localhost"
            or hostname_lower.endswith(".local")
            or hostname_lower.endswith(".internal")
            or hostname_lower.endswith(".localhost")
        ):
            raise SSRFSecurityError(
                f"Disallowed hostname '{hostname}': access to local destinations is prohibited"
            )

        # Resolve IP addresses for the hostname
        port = parsed.port or (443 if scheme == "https" else 80)
        try:
            addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            raise SSRFSecurityError(
                f"Failed to resolve DNS for hostname '{hostname}': {exc}"
            ) from exc

        if not addr_info:
            raise SSRFSecurityError(f"No IP address resolved for hostname '{hostname}'")

        for entry in addr_info:
            ip_str = entry[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError as exc:
                raise SSRFSecurityError(f"Malformed IP address '{ip_str}' resolved: {exc}") from exc

            # Check for IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1)
            if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                ip = ip.ipv4_mapped

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_unspecified
                or ip.is_multicast
            ):
                raise SSRFSecurityError(
                    f"Disallowed IP destination '{ip}' resolved for hostname '{hostname}'"
                )

    async def fetch_source(self, url: str) -> RetrievedSource:
        """Fetch webpage with strict SSRF validation, content-type checks, and streaming size limits."""
        logger.info("Initiating source retrieval for URL: %s", url)
        try:
            self.validate_url_safety(url)
        except SSRFSecurityError as exc:
            logger.warning("SSRF check blocked URL '%s': %s", url, exc.message)
            return RetrievedSource(
                url=url,
                final_url=url,
                status_code=0,
                is_accessible=False,
                error=f"SSRF violation: {exc.message}",
            )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36 OutmateGTM/0.1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
        }

        current_url = url
        redirect_count = 0

        client = self._custom_client or httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,
            verify=True,
        )

        should_close_client = self._custom_client is None

        try:
            while redirect_count <= self.MAX_REDIRECTS:
                self.validate_url_safety(current_url)

                async with client.stream(
                    "GET",
                    current_url,
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    status = response.status_code

                    # Handle Redirects
                    if status in (301, 302, 303, 307, 308):
                        location = response.headers.get("Location")
                        if not location:
                            return RetrievedSource(
                                url=url,
                                final_url=current_url,
                                status_code=status,
                                is_accessible=False,
                                error=f"HTTP {status} redirect without Location header",
                            )

                        next_url = urljoin(current_url, location)
                        redirect_count += 1
                        if redirect_count > self.MAX_REDIRECTS:
                            return RetrievedSource(
                                url=url,
                                final_url=next_url,
                                status_code=status,
                                is_accessible=False,
                                error=f"Exceeded max redirects ({self.MAX_REDIRECTS})",
                            )

                        logger.debug("Following redirect %d to %s", redirect_count, next_url)
                        current_url = next_url
                        continue

                    # Validate HTTP status
                    if status != 200:
                        logger.warning(
                            "Source retrieval failed for '%s' with HTTP status %d",
                            current_url,
                            status,
                        )
                        return RetrievedSource(
                            url=url,
                            final_url=current_url,
                            status_code=status,
                            is_accessible=False,
                            error=f"HTTP {status}",
                        )

                    # Validate Content-Type
                    raw_content_type = response.headers.get("Content-Type", "")
                    content_type = raw_content_type.split(";")[0].strip().lower()
                    if content_type not in self.ALLOWED_CONTENT_TYPES:
                        logger.warning(
                            "Rejected unsupported Content-Type '%s' for '%s'",
                            content_type,
                            current_url,
                        )
                        return RetrievedSource(
                            url=url,
                            final_url=current_url,
                            status_code=status,
                            content_type=raw_content_type,
                            is_accessible=False,
                            error=f"Unsupported Content-Type '{raw_content_type}'",
                        )

                    # Stream body with size limitation
                    chunks: list[bytes] = []
                    total_bytes = 0

                    async for chunk in response.aiter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > self.MAX_BODY_BYTES:
                            logger.warning(
                                "Payload size exceeded limit (%d bytes) for '%s'",
                                self.MAX_BODY_BYTES,
                                current_url,
                            )
                            return RetrievedSource(
                                url=url,
                                final_url=current_url,
                                status_code=status,
                                content_type=raw_content_type,
                                is_accessible=False,
                                error=f"Response exceeded size limit ({self.MAX_BODY_BYTES} bytes)",
                            )
                        chunks.append(chunk)

                    raw_html = b"".join(chunks).decode("utf-8", errors="replace")
                    logger.info(
                        "Successfully retrieved %s (%d bytes, HTTP 200)", current_url, total_bytes
                    )

                    return RetrievedSource(
                        url=url,
                        final_url=current_url,
                        status_code=status,
                        raw_html=raw_html,
                        content_type=raw_content_type,
                        is_accessible=True,
                        error=None,
                    )

            return RetrievedSource(
                url=url,
                final_url=current_url,
                status_code=0,
                is_accessible=False,
                error="Exceeded redirect loop limit",
            )

        except httpx.TimeoutException:
            logger.warning(
                "Source retrieval timed out for '%s' (timeout=%.1fs)", current_url, self.timeout
            )
            return RetrievedSource(
                url=url,
                final_url=current_url,
                status_code=0,
                is_accessible=False,
                error=f"Connection timed out after {self.timeout}s",
            )
        except httpx.HTTPError as exc:
            logger.warning("HTTP connection error for '%s': %s", current_url, exc)
            return RetrievedSource(
                url=url,
                final_url=current_url,
                status_code=0,
                is_accessible=False,
                error=f"Network error: {exc}",
            )
        except Exception as exc:
            logger.error("Unexpected error retrieving '%s': %s", current_url, exc)
            return RetrievedSource(
                url=url,
                final_url=current_url,
                status_code=0,
                is_accessible=False,
                error=f"Retrieval error: {exc}",
            )
        finally:
            if should_close_client:
                await client.aclose()
