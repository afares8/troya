"""Browser automation with Playwright for E2E testing and web scraping."""

from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success


def check_playwright() -> bool:
    try:
        import playwright.sync_api
        return True
    except ImportError:
        return False


def run_browser_test(url: str, screenshot: str | None = None) -> dict[str, Any]:
    """Open a URL, take screenshot, extract text."""
    if not check_playwright():
        print_error("playwright not installed. Run: pip install playwright && playwright install")
        return {"error": "playwright not installed"}

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            title = page.title()
            text = page.evaluate("() => document.body.innerText")[:1000]
            result = {"url": url, "title": title, "text": text}
            if screenshot:
                page.screenshot(path=screenshot)
                result["screenshot"] = screenshot
            browser.close()
            return result
    except Exception as e:
        return {"error": str(e)}


def test_local_app(url: str = "http://127.0.0.1:8765") -> dict[str, Any]:
    """Test the Cascade Web IDE is running."""
    print_info(f"Testing {url}...")
    return run_browser_test(url, screenshot="/tmp/cascade_test.png")
