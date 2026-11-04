"""HTML content extraction and textual normalization service."""

import json
import re
from datetime import datetime

from bs4 import BeautifulSoup, Comment, Tag
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger("services.content_extraction")


class ExtractedPageContent(BaseModel):
    """Normalized structured content extracted from an HTML page."""

    title: str = Field(default="", description="Page title")
    canonical_url: str | None = Field(default=None, description="Declared canonical URL")
    meta_description: str | None = Field(default=None, description="Meta tag description")
    main_text: str = Field(default="", description="Clean main textual body")
    paragraphs: list[str] = Field(
        default_factory=list, description="Extracted distinct text paragraphs"
    )
    published_date: datetime | None = Field(
        default=None, description="Discovered publication timestamp"
    )
    modified_date: datetime | None = Field(
        default=None, description="Discovered last modification timestamp"
    )


class ContentExtractionService:
    """Extracts clean article text, metadata, and structured chunks from HTML."""

    BOILERPLATE_TAGS = {
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "noscript",
        "svg",
        "form",
        "button",
        "iframe",
        "dialog",
    }

    DATE_FORMATS = (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    )

    def extract(self, html: str, fallback_url: str = "") -> ExtractedPageContent:
        """Parse HTML string and extract clean text, headers, and metadata."""
        if not html or not html.strip():
            return ExtractedPageContent()

        soup = BeautifulSoup(html, "html.parser")

        # 1. Remove comments
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()

        # 2. Extract title
        title = ""
        og_title = soup.find("meta", property="og:title")
        if isinstance(og_title, Tag) and og_title.get("content"):
            title = str(og_title["content"]).strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # 3. Extract canonical URL
        canonical_url: str | None = None
        canonical_tag = soup.find("link", rel="canonical")
        if isinstance(canonical_tag, Tag) and canonical_tag.get("href"):
            canonical_url = str(canonical_tag["href"]).strip()

        # 4. Extract meta description
        meta_description: str | None = None
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
            "meta", property="og:description"
        )
        if isinstance(desc_tag, Tag) and desc_tag.get("content"):
            meta_description = str(desc_tag["content"]).strip()

        # 5. Extract publication and modification dates
        pub_date, mod_date = self._extract_dates(soup)

        # 6. Remove boilerplate and navigation elements
        for tag_name in self.BOILERPLATE_TAGS:
            for element in soup.find_all(tag_name):
                element.decompose()

        # Remove elements by class / id heuristic (cookie banners, menus, popups)
        cookie_pattern = re.compile(
            r"cookie|banner|consent|modal|popup|newsletter|advertisement", re.I
        )
        for element in soup.find_all(attrs={"class": cookie_pattern}) + soup.find_all(
            attrs={"id": cookie_pattern}
        ):
            element.decompose()

        # 7. Extract main text paragraphs
        paragraphs: list[str] = []
        # Look for typical content containers first, fallback to all paragraphs
        content_root = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.body
            or soup
        )

        if isinstance(content_root, Tag):
            for p in content_root.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
                raw_text = p.get_text(separator=" ", strip=True)
                cleaned = self._clean_whitespace(raw_text)
                if len(cleaned) >= 25:  # Skip trivial snippets
                    paragraphs.append(cleaned)

        full_text = "\n\n".join(paragraphs)

        return ExtractedPageContent(
            title=title,
            canonical_url=canonical_url or (fallback_url if fallback_url else None),
            meta_description=meta_description,
            main_text=full_text,
            paragraphs=paragraphs,
            published_date=pub_date,
            modified_date=mod_date,
        )

    def _clean_whitespace(self, text: str) -> str:
        """Collapse redundant spaces, tabs, and newlines."""
        return re.sub(r"\s+", " ", text).strip()

    def _parse_date_string(self, date_str: str) -> datetime | None:
        """Attempt to parse ISO 8601 or common date formats."""
        if not date_str:
            return None
        date_clean = date_str.strip()
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_clean, fmt)
            except ValueError:
                continue
        return None

    def _extract_dates(self, soup: BeautifulSoup) -> tuple[datetime | None, datetime | None]:
        """Discover publication and modification timestamps from meta tags and JSON-LD."""
        pub_date: datetime | None = None
        mod_date: datetime | None = None

        # Check OpenGraph & Schema meta tags
        for name in (
            "article:published_time",
            "og:published_time",
            "datePublished",
            "publication_date",
        ):
            tag = soup.find("meta", property=name) or soup.find("meta", attrs={"name": name})
            if isinstance(tag, Tag) and tag.get("content"):
                pub_date = self._parse_date_string(str(tag["content"]))
                if pub_date:
                    break

        for name in (
            "article:modified_time",
            "og:modified_time",
            "dateModified",
            "last_updated",
        ):
            tag = soup.find("meta", property=name) or soup.find("meta", attrs={"name": name})
            if isinstance(tag, Tag) and tag.get("content"):
                mod_date = self._parse_date_string(str(tag["content"]))
                if mod_date:
                    break

        # Check JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            if script.string:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if not pub_date and "datePublished" in data:
                            pub_date = self._parse_date_string(str(data["datePublished"]))
                        if not mod_date and "dateModified" in data:
                            mod_date = self._parse_date_string(str(data["dateModified"]))
                except Exception:
                    pass

        return pub_date, mod_date
