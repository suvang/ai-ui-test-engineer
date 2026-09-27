import json
from collections.abc import Sequence

from ui_test_engineer.types import Control


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
        lines.append(
            "        page.get_by_role('heading', name="
            f"{json.dumps(heading)}).wait_for(state='visible')"
        )
    flow: Control | None = None
    for control in controls:
        if control.kind == "button":
            lines.append(
                "        page.get_by_role('button', name="
                f"{json.dumps(control.name)}).wait_for(state='visible')"
            )
        elif control.kind == "form_field":
            lines.append(
                "        field = page.get_by_role('textbox', name="
                f"{json.dumps(control.name)})"
            )
            lines.append("        field.fill('2')")
            lines.append("        assert field.input_value() == '2'")
        elif control.kind == "navigation_link":
            flow = control
    if flow is not None:
        lines.append(
            f"        page.get_by_role('link', name={json.dumps(flow.name)}).click()"
        )
        lines.append("        page.wait_for_load_state('domcontentloaded')")
        if flow.destination:
            lines.append(
                "        page.get_by_role('heading', name="
                f"{json.dumps(flow.destination)}).wait_for(state='visible')"
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
            controls.append(
                Control(
                    kind,
                    name,
                    str(destination) if isinstance(destination, str) else "",
                )
            )
    heading = payload.get("heading", "")
    url = payload.get("url", "")
    return render_script(
        str(url),
        str(heading) if isinstance(heading, str) else "",
        controls,
    )
