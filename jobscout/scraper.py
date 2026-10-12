from __future__ import annotations

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

MAX_CHARS = 15_000
MAX_LINKS = 150
NAV_TIMEOUT_MS = 20_000
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)


def _goto(page, url: str, errors: list[str]) -> bool:
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        return True
    except PlaywrightTimeoutError:
        errors.append(f"timeout loading {url}")
    except PlaywrightError as exc:
        errors.append(f"error loading {url}: {exc}")
    return False


def scrape_careers_page(url: str) -> tuple[str, list[tuple[str, str]], list[str]]:
    """Render the careers page and pull out visible text plus candidate job links.

    Returns (page_text, links, errors) where links is a list of (link_text, href).
    Never raises: a dead/blocking page just yields empty results and an error entry.
    """
    errors: list[str] = []
    page_text = ""
    links: list[tuple[str, str]] = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
            if _goto(page, url, errors):
                # Many ATS boards (Greenhouse, Lever, Workday) lazy-render the list
                # or paginate behind a "load more" button; a couple of scrolls
                # and a best-effort click pick up more of it without over-engineering.
                for _ in range(5):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(300)
                for label in ("Load more", "Show more", "View more"):
                    try:
                        button = page.get_by_text(label, exact=False)
                        if button.count() > 0:
                            button.first.click(timeout=2000)
                            page.wait_for_timeout(500)
                    except PlaywrightError:
                        pass

                page_text = page.inner_text("body")[:MAX_CHARS]
                raw_links = page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => [e.innerText.trim(), e.href])",
                )
                seen = set()
                for text, href in raw_links:
                    if not href or href in seen:
                        continue
                    seen.add(href)
                    links.append((text[:120], href))
                    if len(links) >= MAX_LINKS:
                        break
            browser.close()
    except PlaywrightError as exc:
        errors.append(f"could not start browser: {exc}")

    if not page_text:
        errors.append(f"could not retrieve any content from {url}")

    return page_text, links, errors


def scrape_job_page_text(url: str) -> tuple[str, list[str]]:
    """Fetch a single job posting's own page and return its visible text.

    Lighter than scrape_careers_page: no link harvesting or load-more clicking,
    since job detail pages are usually a single static description. The raw text
    is kept as-is (not parsed into fields) so a future CV-matching step has the
    full responsibilities/requirements/stack to reason over.
    """
    errors: list[str] = []
    page_text = ""

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
            if _goto(page, url, errors):
                page_text = page.inner_text("body")[:MAX_CHARS]
            browser.close()
    except PlaywrightError as exc:
        errors.append(f"could not start browser: {exc}")

    return page_text, errors
