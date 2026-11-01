import base64
import html
from typing import Literal
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.sync_api import Browser, BrowserContext, Locator, Page, Request, Response, sync_playwright

from ui_test_engineer.types import ApiCall, Finding, Navigation

Role = Literal["link", "button"]
_API_TYPES = {"xhr", "fetch"}


def audit(url: str) -> tuple[tuple[Finding, ...], tuple[ApiCall, ...], str, str, str]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.set_default_timeout(8000)
            watch = _Watch()
            watch.listen(page.context)
            page.goto(url, wait_until="domcontentloaded")
            _settle(page)
            page_calls = _dedupe(watch.calls)
            watch.clear()
            snapshot = _clean(page.locator("body").inner_text())[:2000]
            page_screenshot = _picture(page)
            failed_on_open = tuple(call for call in page_calls if not call.ok)
            page_network = _network_tab(browser, failed_on_open) if failed_on_open else ""
            seen_failures = {(call.method, call.name) for call in failed_on_open}
            ctas = _collect(page)
            findings = tuple(
                _exercise(browser, page, watch, url, kind, name, href, seen_failures)
                for kind, name, href in ctas
            )
            return findings, tuple(page_calls), snapshot, page_screenshot, page_network
        finally:
            browser.close()


def _exercise(
    browser: Browser,
    page: Page,
    watch: "_Watch",
    start: str,
    kind: Role,
    name: str,
    href: str,
    landing_failures: set[tuple[str, str]],
) -> Finding:
    _open(page, start)
    watch.clear()
    target = _find(page, kind, name, href)
    if target is None:
        page.wait_for_timeout(400)
        target = _find(page, kind, name, href)
    if target is None:
        return _finding(
            name,
            kind,
            "missed",
            "",
            "The call to action was not on the page.",
            "It could not be clicked.",
            (),
            _picture(page),
        )

    _mark(target)
    image = _picture(page)
    pages_before = set(page.context.pages)
    click_error = ""
    try:
        _activate(target)
        if _expects_navigation(href) and not _new_pages(page.context, pages_before):
            expected = urljoin(start, href)
            try:
                page.wait_for_url(lambda landed: _same_page(landed, expected), timeout=4000)
            except Exception:
                pass
        page.wait_for_timeout(200)
        _settle(page)
    except Exception as error:
        click_error = str(error)

    landed, opened_new, subject = _landed(page, pages_before, start)
    moved = opened_new or not _same_page(landed, start)
    arrived = _expects_navigation(href) and _same_page(landed, urljoin(start, href))
    rendered = _rendered(subject) if moved else False
    network = _destination_failures(watch, landed) if moved else ()
    if click_error and not arrived:
        if opened_new:
            subject.close()
        watch.clear()
        return _finding(name, kind, "failed", page.url, "The click failed.", click_error, (), image)
    status = watch.document_status[-1] if watch.document_status else None
    navigation, detail = _navigation(href, start, landed, moved, status, watch.document_error, rendered)
    if opened_new:
        subject.close()
    calls = () if moved else _owned(list(watch.calls), landing_failures)
    failed_requests = tuple(call for call in (*network, *calls) if not call.ok)
    network_image = _network_tab(browser, failed_requests) if failed_requests else ""
    watch.clear()
    action = _action(navigation, opened_new, landed, moved, calls)
    if navigation == "passed" and network:
        action = f"{action} The page rendered."
    if navigation == "failed" and not detail:
        detail = f"Navigation to {landed} failed."
    api_detail = _api_detail(calls)
    if api_detail:
        detail = f"{detail} {api_detail}".strip()
    return _finding(
        name,
        kind,
        navigation,
        landed if moved else "",
        action,
        detail,
        calls,
        image,
        network,
        network_image,
    )


def _mark(locator: Locator) -> None:
    try:
        locator.scroll_into_view_if_needed(timeout=1000)
    except Exception:
        pass
    try:
        locator.evaluate(_MARK)
    except Exception:
        pass


_MARK = """el => {
  el.scrollIntoView({block: "center", inline: "center"});
  document.querySelectorAll("[data-cta-mark]").forEach((node) => node.remove());
  const rect = el.getBoundingClientRect();
  const pad = 10;
  const boxLeft = Math.max(8, rect.left - pad);
  const boxTop = Math.max(8, rect.top - pad);
  const boxWidth = Math.max(rect.width, 36) + pad * 2;
  const boxHeight = Math.max(rect.height, 28) + pad * 2;
  const box = document.createElement("div");
  box.setAttribute("data-cta-mark", "true");
  box.style.cssText = [
    "position:fixed",
    "left:" + boxLeft + "px",
    "top:" + boxTop + "px",
    "width:" + boxWidth + "px",
    "height:" + boxHeight + "px",
    "border:6px solid #ff1f1f",
    "box-shadow:0 0 0 5px #ffffff, 0 0 0 11px #ff1f1f",
    "border-radius:2px",
    "z-index:2147483646",
    "pointer-events:none",
    "box-sizing:border-box",
  ].join(";");
  const arrowWidth = 230;
  const arrowHeight = 64;
  const roomLeft = boxLeft > arrowWidth + 12;
  const roomRight = window.innerWidth - (boxLeft + boxWidth) > arrowWidth + 12;
  const roomAbove = boxTop > arrowHeight + 12;
  let point = "right";
  let left = boxLeft - arrowWidth - 6;
  let top = boxTop + boxHeight / 2 - arrowHeight / 2;
  if (!roomLeft && roomRight) {
    point = "left";
    left = boxLeft + boxWidth + 6;
  } else if (!roomLeft && !roomRight && roomAbove) {
    point = "down";
    left = Math.max(8, boxLeft + boxWidth / 2 - arrowWidth / 2);
    top = boxTop - arrowHeight - 8;
  } else if (!roomLeft && !roomRight) {
    point = "up";
    left = Math.max(8, boxLeft);
    top = boxTop + boxHeight + 8;
  }
  const marker = document.createElement("div");
  marker.setAttribute("data-cta-mark", "true");
  marker.style.cssText = "position:fixed;left:" + left + "px;top:" + top + "px;z-index:2147483647;display:flex;align-items:center;gap:0;pointer-events:none;";
  const label = document.createElement("div");
  label.textContent = "Testing this";
  label.style.cssText = "background:#ff1f1f;color:#fff;font:700 22px/1 Arial,sans-serif;padding:10px 14px;border-radius:8px;box-shadow:0 2px 0 #ffffff";
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "78");
  svg.setAttribute("height", "48");
  svg.setAttribute("viewBox", "0 0 78 48");
  svg.style.flex = "0 0 auto";
  const shaft = document.createElementNS("http://www.w3.org/2000/svg", "line");
  const head = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
  shaft.setAttribute("stroke", "#ff1f1f");
  shaft.setAttribute("stroke-width", "8");
  head.setAttribute("fill", "#ff1f1f");
  if (point === "right") {
    shaft.setAttribute("x1", "0"); shaft.setAttribute("y1", "24"); shaft.setAttribute("x2", "50"); shaft.setAttribute("y2", "24");
    head.setAttribute("points", "46,8 76,24 46,40");
    marker.append(label, svg);
  } else if (point === "left") {
    shaft.setAttribute("x1", "28"); shaft.setAttribute("y1", "24"); shaft.setAttribute("x2", "78"); shaft.setAttribute("y2", "24");
    head.setAttribute("points", "32,8 2,24 32,40");
    marker.append(svg, label);
  } else if (point === "down") {
    svg.setAttribute("width", "48"); svg.setAttribute("height", "64");
    shaft.setAttribute("x1", "24"); shaft.setAttribute("y1", "0"); shaft.setAttribute("x2", "24"); shaft.setAttribute("y2", "36");
    head.setAttribute("points", "8,32 24,62 40,32");
    marker.style.flexDirection = "column";
    marker.append(label, svg);
  } else {
    svg.setAttribute("width", "48"); svg.setAttribute("height", "64");
    shaft.setAttribute("x1", "24"); shaft.setAttribute("y1", "28"); shaft.setAttribute("x2", "24"); shaft.setAttribute("y2", "64");
    head.setAttribute("points", "8,32 24,2 40,32");
    marker.style.flexDirection = "column";
    marker.append(svg, label);
  }
  svg.append(shaft, head);
  document.body.append(box, marker);
}"""


def _activate(locator: Locator) -> None:
    try:
        locator.click(timeout=5000)
    except Exception:
        locator.click(timeout=5000, force=True)


def _open(page: Page, start: str) -> None:
    page.goto(start, wait_until="domcontentloaded")
    _settle(page)


def _settle(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=2500)
    except Exception:
        page.wait_for_timeout(600)


def _collect(page: Page) -> list[tuple[Role, str, str]]:
    found: list[tuple[Role, str, str]] = []
    seen: set[tuple[Role, str, str]] = set()
    roles: tuple[Role, ...] = ("link", "button")
    for role in roles:
        locator = page.get_by_role(role)
        for index in range(locator.count()):
            item = locator.nth(index)
            if not item.is_visible():
                continue
            name = _clean(item.get_attribute("aria-label") or "") or _clean(item.inner_text())
            if not name:
                continue
            href = item.get_attribute("href") or ""
            key = (role, name, href)
            if key in seen:
                continue
            seen.add(key)
            found.append(key)
    return found


def _find(page: Page, kind: Role, name: str, href: str) -> Locator | None:
    found = _pick(page.get_by_role(kind, name=name, exact=True), href)
    if found is None:
        found = _pick(page.get_by_role(kind, name=name, exact=False), href)
    if found is None and href and kind == "link":
        found = _pick(page.locator("a[href]"), href)
    return found


def _pick(locator: Locator, href: str) -> Locator | None:
    fallback: Locator | None = None
    for index in range(locator.count()):
        candidate = locator.nth(index)
        if href and (candidate.get_attribute("href") or "") != href:
            continue
        if fallback is None:
            fallback = candidate
        try:
            if candidate.is_visible():
                return candidate
        except Exception:
            continue
    return fallback


def _navigation(
    href: str,
    start: str,
    landed: str,
    moved: bool,
    status: int | None,
    document_error: list[str],
    rendered: bool,
) -> tuple[Navigation, str]:
    document_failed = bool(document_error) or (status is not None and status >= 400)
    if not _expects_navigation(href):
        if not moved:
            return "stayed", ""
        if document_failed and not rendered:
            return "failed", _document_reason(landed, status, document_error)
        return "passed", ""
    expected = urljoin(start, href)
    if not _same_page(landed, expected):
        return "failed", f"Did not navigate to {expected}. Stayed on {landed}."
    if document_failed and not rendered:
        return "failed", _document_reason(landed, status, document_error)
    return "passed", ""


def _rendered(page: Page) -> bool:
    if page.url.startswith("chrome-error:"):
        return False
    try:
        text = _clean(page.locator("body").inner_text())
    except Exception:
        return False
    return len(text) >= 80


def _destination_failures(watch: "_Watch", landed: str) -> tuple[ApiCall, ...]:
    path = urlparse(landed).path.rstrip("/") or "/"
    found: list[ApiCall] = []
    for call in (*watch.documents, *watch.calls):
        if call.ok:
            continue
        if (urlparse(call.url).path.rstrip("/") or "/") != path:
            continue
        found.append(call)
    if not found:
        status = watch.document_status[-1] if watch.document_status else None
        if status is not None and status >= 400:
            found.append(ApiCall(path, "GET", landed, status, False, "", "document"))
    return tuple(_dedupe(found))


def _network_tab(browser: Browser, failures: tuple[ApiCall, ...]) -> str:
    panel = browser.new_page(viewport={"width": 1280, "height": 720})
    try:
        panel.set_content(_network_html(failures))
        return _picture(panel)
    except Exception:
        return ""
    finally:
        panel.close()


def _network_html(failures: tuple[ApiCall, ...]) -> str:
    rows: list[str] = []
    for call in failures:
        status = "failed" if call.status is None else str(call.status)
        kind = html.escape(call.resource or "fetch")
        rows.append(
            "<tr>"
            f"<td class='name'>{html.escape(call.name)}</td>"
            f"<td class='status'>{html.escape(status)}</td>"
            f"<td>{kind}</td>"
            f"<td>{html.escape(call.method)}</td>"
            f"<td class='url'>{html.escape(call.url)}</td>"
            "</tr>"
        )
    count = len(failures)
    noun = "request" if count == 1 else "requests"
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #fff; color: #202124; font: 16px/1.4 "Segoe UI", Arial, sans-serif; }}
    header {{ display: flex; align-items: center; gap: 18px; height: 52px; padding: 0 16px; background: #f1f3f4; border-bottom: 1px solid #dadce0; }}
    header strong {{ font-size: 18px; }}
    .chip {{ background: #d93025; color: #fff; border-radius: 999px; padding: 4px 12px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ text-align: left; font-size: 13px; letter-spacing: .04em; text-transform: uppercase; color: #5f6368; background: #f8f9fa; padding: 10px 12px; border-bottom: 1px solid #dadce0; }}
    td {{ padding: 14px 12px; border-bottom: 1px solid #e8eaed; vertical-align: top; }}
    td.name, td.status {{ color: #d93025; font-weight: 700; }}
    td.url {{ word-break: break-all; }}
    footer {{ padding: 12px 16px; color: #d93025; font-weight: 700; background: #f8f9fa; border-top: 1px solid #dadce0; }}
  </style>
</head>
<body>
  <header><strong>Network</strong><span class="chip">Failed</span><span>{count} {noun}</span></header>
  <table>
    <thead><tr><th>Name</th><th>Status</th><th>Type</th><th>Method</th><th>URL</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  <footer>{count} failed {noun}</footer>
</body>
</html>"""


def _document_reason(landed: str, status: int | None, document_error: list[str]) -> str:
    if document_error:
        return f"Navigation to {landed} failed. {document_error[-1]}"
    return f"Navigation to {landed} returned {status}."


def _expects_navigation(href: str) -> bool:
    lowered = href.strip().lower()
    if not lowered or lowered.startswith("#"):
        return False
    return not lowered.startswith(("mailto:", "javascript:", "tel:"))


def _owned(calls: list[ApiCall], landing_failures: set[tuple[str, str]]) -> tuple[ApiCall, ...]:
    kept: list[ApiCall] = []
    for call in calls:
        if _is_prefetch(call.url):
            continue
        if not call.ok and (call.method, call.name) in landing_failures:
            continue
        kept.append(call)
    return tuple(_dedupe(kept))


def _action(
    navigation: Navigation,
    opened_new: bool,
    landed: str,
    moved: bool,
    calls: tuple[ApiCall, ...],
) -> str:
    if navigation == "missed":
        return "The call to action was not on the page."
    parts: list[str] = []
    if navigation == "stayed":
        parts.append("Stays on the page.")
    elif moved:
        verb = "Opens" if opened_new else "Navigates to"
        parts.append(f"{verb} {landed}.")
    elif navigation == "failed":
        parts.append("Did not navigate.")
    if calls:
        names = ", ".join(f"{call.method} {call.name}" for call in calls)
        parts.append(f"Calls {names}.")
    elif navigation == "stayed":
        parts.append("Does not call an API.")
    return " ".join(parts)


def _api_detail(calls: tuple[ApiCall, ...]) -> str:
    reasons: list[str] = []
    for call in calls:
        if call.ok:
            continue
        status_text = f"status {call.status}" if call.status is not None else "no response"
        extra = f" {call.detail}" if call.detail else ""
        reasons.append(f"{call.method} {call.name} failed ({status_text}).{extra}")
    return " ".join(reasons)


def _finding(
    name: str,
    kind: str,
    navigation: Navigation,
    destination: str,
    action: str,
    detail: str,
    calls: tuple[ApiCall, ...],
    screenshot: str,
    network: tuple[ApiCall, ...] = (),
    network_screenshot: str = "",
) -> Finding:
    passed = navigation in {"passed", "stayed"} and all(call.ok for call in calls)
    return Finding(
        name,
        kind,
        navigation,
        destination,
        action,
        detail,
        calls,
        passed,
        screenshot,
        network,
        network_screenshot,
    )


def _picture(page: Page) -> str:
    try:
        return base64.b64encode(page.screenshot(type="png")).decode("ascii")
    except Exception:
        return ""


class _Watch:
    def __init__(self) -> None:
        self.calls: list[ApiCall] = []
        self.documents: list[ApiCall] = []
        self.document_status: list[int] = []
        self.document_error: list[str] = []

    def listen(self, context: BrowserContext) -> None:
        context.on("response", self._on_response)
        context.on("requestfailed", self._on_failed)

    def stop(self, context: BrowserContext) -> None:
        context.remove_listener("response", self._on_response)
        context.remove_listener("requestfailed", self._on_failed)

    def clear(self) -> None:
        self.calls.clear()
        self.documents.clear()
        self.document_status.clear()
        self.document_error.clear()

    def _on_response(self, response: Response) -> None:
        request = response.request
        if request.resource_type == "document" and _main_document(response):
            self.document_status.append(response.status)
            self.documents.append(
                ApiCall(
                    _api_name(response.url),
                    request.method,
                    response.url,
                    response.status,
                    response.status < 400,
                    response.status_text or "",
                    "document",
                )
            )
        if request.resource_type not in _API_TYPES or _cancelled(response.status_text):
            return
        detail = response.status_text or ""
        if response.status >= 400:
            try:
                body = response.text()[:180].strip()
            except Exception:
                body = ""
            if body:
                detail = f"{detail} {body}".strip()
        self.calls.append(
            ApiCall(
                _api_name(response.url),
                request.method,
                response.url,
                response.status,
                response.status < 400,
                detail,
                request.resource_type,
            )
        )

    def _on_failed(self, request: Request) -> None:
        message = request.failure or "The request failed."
        if _cancelled(message):
            return
        if request.resource_type == "document":
            self.document_error.append(message)
        if request.resource_type not in _API_TYPES:
            return
        self.calls.append(
            ApiCall(_api_name(request.url), request.method, request.url, None, False, message, request.resource_type)
        )


def _main_document(response: Response) -> bool:
    frame = response.frame
    return frame == frame.page.main_frame


def _new_pages(context: BrowserContext, pages_before: set[Page]) -> list[Page]:
    return [item for item in context.pages if item not in pages_before]


def _landed(page: Page, pages_before: set[Page], start: str) -> tuple[str, bool, Page]:
    new_pages = _new_pages(page.context, pages_before)
    if not new_pages:
        return page.url, False, page
    popup = new_pages[-1]
    try:
        popup.wait_for_load_state("domcontentloaded", timeout=8000)
    except Exception:
        pass
    return popup.url or start, True, popup


def _dedupe(calls: list[ApiCall]) -> list[ApiCall]:
    found: list[ApiCall] = []
    seen: set[tuple[str, str, int | None, bool]] = set()
    for call in calls:
        key = (call.method, call.url, call.status, call.ok)
        if key in seen:
            continue
        seen.add(key)
        found.append(call)
    return found


def _is_prefetch(url: str) -> bool:
    return "_rsc" in parse_qs(urlparse(url).query)


def _cancelled(message: str) -> bool:
    return "ERR_ABORTED" in message


def _api_name(url: str) -> str:
    return urlparse(url).path or "/"


def _same_page(left: str, right: str) -> bool:
    return _page_key(left) == _page_key(right)


def _page_key(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _clean(text: str) -> str:
    return " ".join(text.split())
