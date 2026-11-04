"""Unit tests for HTML content extraction and textual normalization."""

from app.services.content_extraction import ContentExtractionService


def test_extract_strips_boilerplate_and_scripts() -> None:
    """Verify scripts, styles, navigation, footer, and cookie banners are stripped."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vercel: Build and deploy the Web</title>
        <meta name="description" content="Frontend cloud platform for developers.">
        <link rel="canonical" href="https://vercel.com/home">
        <script>console.log("analytics");</script>
        <style>body { color: black; }</style>
    </head>
    <body>
        <nav><a href="/login">Login</a></nav>
        <div class="cookie-banner-popup">We use cookies to track you.</div>
        <main>
            <h1>Develop. Preview. Ship.</h1>
            <p>Vercel is the platform for frontend developers, providing the speed and reliability innovators need.</p>
            <p>It enables teams to deploy web applications instantly with zero configuration.</p>
        </main>
        <footer><p>Copyright 2024 Vercel Inc</p></footer>
    </body>
    </html>
    """

    extractor = ContentExtractionService()
    content = extractor.extract(html, fallback_url="https://vercel.com")

    assert content.title == "Vercel: Build and deploy the Web"
    assert content.canonical_url == "https://vercel.com/home"
    assert content.meta_description == "Frontend cloud platform for developers."
    assert "analytics" not in content.main_text
    assert "cookies" not in content.main_text
    assert "Develop. Preview. Ship." in content.main_text
    assert "platform for frontend developers" in content.main_text
    assert len(content.paragraphs) >= 2


def test_extract_dates_from_meta_tags() -> None:
    """Verify published dates are parsed from article:published_time meta tags."""
    html = """
    <html>
    <head>
        <meta property="article:published_time" content="2024-05-15T14:30:00Z">
        <meta property="article:modified_time" content="2024-05-16T10:00:00Z">
    </head>
    <body><p>Article content about modern cloud technology and infrastructure.</p></body>
    </html>
    """
    extractor = ContentExtractionService()
    content = extractor.extract(html)

    assert content.published_date is not None
    assert content.published_date.year == 2024
    assert content.published_date.month == 5
    assert content.published_date.day == 15

    assert content.modified_date is not None
    assert content.modified_date.day == 16


def test_extract_handles_empty_or_malformed_html() -> None:
    """Verify malformed or empty HTML does not raise exceptions."""
    extractor = ContentExtractionService()
    empty_result = extractor.extract("")
    assert empty_result.main_text == ""
    assert empty_result.title == ""

    malformed_result = extractor.extract("<div><p>Unclosed paragraph")
    assert "Unclosed paragraph" in malformed_result.main_text

