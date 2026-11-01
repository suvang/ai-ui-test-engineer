import base64
import json
from urllib.parse import urljoin, urlparse

from playwright.sync_api import Locator, Page, sync_playwright

from ui_test_engineer.script import _url_glob
from ui_test_engineer.types import Control

MAX_CONTROLS = 8


class Observation:
    def __init__(
        self,
        url: str,
        heading: str,
        snapshot: str,
        screenshot: bytes,
        controls: tuple[Control, ...],
    ) -> None:
        self.url = url
        self.heading = heading
        self.snapshot = snapshot
        self.screenshot = screenshot
        self.controls = controls

    def payload_json(self) -> str:
        return json.dumps(
            {
                "url": self.url,
                "heading": self.heading,
                "snapshot": self.snapshot,
                "screenshot_bytes": len(self.screenshot),
                "screenshot_base64": base64.b64encode(self.screenshot).decode("ascii"),
                "controls": [control.as_dict() for control in self.controls],
            }
        )


def explore(url: str) -> Observation:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_default_timeout(8000)
            page.goto(url, wait_until="domcontentloaded")
            return _read(page, url)
        finally:
            browser.close()


def _read(page: Page, url: str) -> Observation:
    heading = _heading(page)
    buttons = _unique(_names(page.get_by_role("button")))
    fields = _unique(_field_names(page))
    flow = _first_flow(page, url)
    controls: list[Control] = [Control("button", name) for name in buttons]
    controls.extend(Control("form_field", name) for name in fields)
    if flow is not None:
        controls.append(flow)
    kept = _cap(controls)
    snapshot = _snapshot(page)
    screenshot = page.screenshot(type="png")
    return Observation(url, heading, snapshot, screenshot, tuple(kept))


def _clean(text: str) -> str:
    return " ".join(text.split())


def _heading_text(page: Page) -> str:
    headings = page.get_by_role("heading")
    if headings.count() == 0:
        return ""
    return _clean(headings.first.inner_text())


def _heading(page: Page) -> str:
    return _heading_text(page) or _clean(page.title())


def _names(locator: Locator) -> list[str]:
    found: list[str] = []
    for index in range(locator.count()):
        item = locator.nth(index)
        text = _clean(item.inner_text().split("\n")[0])
        if not text:
            text = _clean(item.get_attribute("aria-label") or "")
        if text:
            found.append(text)
    return found


def _field_names(page: Page) -> list[str]:
    fields = page.get_by_role("textbox")
    found: list[str] = []
    for index in range(fields.count()):
        name = fields.nth(index).evaluate(
            """el => {
                const labelled = el.labels && el.labels[0] ? el.labels[0].innerText : "";
                return (el.getAttribute("aria-label") || labelled || el.getAttribute("placeholder") || "").trim();
            }"""
        )
        if isinstance(name, str) and name:
            found.append(_clean(name.split("\n")[0]))
    return found


def _first_flow(page: Page, url: str) -> Control | None:
    links = page.get_by_role("link")
    for index in range(links.count()):
        link = links.nth(index)
        name = _clean(link.inner_text().split("\n")[0])
        href = link.get_attribute("href") or ""
        if not name or not _is_flow_href(url, href):
            continue
        target = urljoin(page.url, href)
        try:
            link.click()
            page.wait_for_url(_url_glob(target), timeout=8000)
        except Exception:
            if _page_key(page.url) == _page_key(url):
                continue
        destination = _heading_text(page)
        landed = page.url
        try:
            page.go_back(wait_until="domcontentloaded")
        except Exception:
            pass
        return Control("navigation_link", name, destination, landed)
    return None


def _page_key(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _is_flow_href(page_url: str, href: str) -> bool:
    if not href or href.startswith(("#", "mailto:", "javascript:")):
        return False
    target = urljoin(page_url, href)
    page = urlparse(page_url)
    dest = urlparse(target)
    if dest.scheme not in {"http", "https"}:
        return False
    if (dest.scheme, dest.netloc) != (page.scheme, page.netloc):
        return False
    return (dest.path, dest.query) != (page.path, page.query)


def _unique(names: list[str]) -> list[str]:
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen


def _cap(controls: list[Control]) -> list[Control]:
    if len(controls) <= MAX_CONTROLS:
        return controls
    flow = [control for control in controls if control.kind == "navigation_link"]
    others = [control for control in controls if control.kind != "navigation_link"]
    room = MAX_CONTROLS - len(flow[:1])
    return others[:room] + flow[:1]


def _snapshot(page: Page) -> str:
    try:
        text = page.locator("body").aria_snapshot()
    except Exception:
        text = page.inner_text("body")
    return text[:4000]
