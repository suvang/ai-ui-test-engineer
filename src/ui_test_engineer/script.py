import json
from collections.abc import Sequence
from urllib.parse import urlparse

from ui_test_engineer.types import Control


def _locator(role: str, name: str) -> str:
    return (
        f"page.get_by_role({json.dumps(role)}, name={json.dumps(name)}, exact=True).first"
    )


def render_script(url: str, heading: str, controls: Sequence[Control]) -> str:
    lines = [
        "from playwright.sync_api import sync_playwright",
        "",
        "def test_target_page() -> None:",
        "    with sync_playwright() as playwright:",
        "        browser = playwright.chromium.launch(headless=True)",
        "        page = browser.new_page()",
        "        page.set_default_timeout(8000)",
        f"        page.goto({json.dumps(url)}, wait_until='domcontentloaded')",
    ]
    if heading:
        lines.append(f"        {_locator('heading', heading)}.wait_for(state='visible')")
    flow: Control | None = None
    for control in controls:
        if control.kind == "button":
            lines.append(f"        {_locator('button', control.name)}.wait_for(state='visible')")
        elif control.kind == "form_field":
            lines.append(f"        field = {_locator('textbox', control.name)}")
            lines.append("        field.fill('2')")
            lines.append("        assert field.input_value() == '2'")
        elif control.kind == "navigation_link":
            flow = control
    if flow is not None:
        lines.append(f"        {_locator('link', flow.name)}.click()")
        if flow.landed_url:
            lines.append(f"        page.wait_for_url({json.dumps(_url_glob(flow.landed_url))})")
        else:
            lines.append("        page.wait_for_load_state('domcontentloaded')")
        if flow.destination:
            lines.append(
                f"        {_locator('heading', flow.destination)}.wait_for(state='visible')"
            )
    lines.extend(
        [
            "        browser.close()",
            "",
            "if __name__ == '__main__':",
            "    test_target_page()",
            "",
        ]
    )
    return "\n".join(lines)


def _url_glob(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}*"


def render_from_observation(payload: dict[str, object], drop: set[str]) -> str:
    raw_controls = payload.get("controls")
    controls: list[Control] = []
    if isinstance(raw_controls, list):
        for item in raw_controls:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", ""))
            kind = item.get("kind", "")
            if kind not in {"button", "form_field", "navigation_link"} or not name or name in drop:
                continue
            destination = item.get("destination", "")
            landed = item.get("landed_url", "")
            controls.append(
                Control(
                    kind,
                    name,
                    str(destination) if isinstance(destination, str) else "",
                    str(landed) if isinstance(landed, str) else "",
                )
            )
    heading = payload.get("heading", "")
    url = payload.get("url", "")
    return render_script(
        str(url),
        str(heading) if isinstance(heading, str) else "",
        controls,
    )
