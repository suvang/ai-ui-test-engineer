"""An Examination proves a Target page with a Test script."""

import json
import socket
import threading
import time
from collections.abc import Iterator
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from ui_test_engineer.api import create_app
from ui_test_engineer.engineer import TestEngineer
from ui_test_engineer.session import ModelTurn, ToolCall, ToolSession, tool_followups

SAMPLE = Path(__file__).parents[1] / "src" / "ui_test_engineer" / "static" / "sample"


class SampleHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(SAMPLE), **kwargs)  # type: ignore[arg-type]

    def log_message(self, format: str, *args: object) -> None:
        return


class ScriptedSession(ToolSession):
    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns = turns
        self.index = 0
        self.results: list[list[tuple[ToolCall, str]]] = []

    def start(self, system: str, user: str, tools: list[dict[str, object]]) -> ModelTurn:
        return self._next()

    def resume(self, results: list[tuple[ToolCall, str]]) -> ModelTurn:
        self.results.append(results)
        return self._next()

    def _next(self) -> ModelTurn:
        turn = self._turns[self.index]
        self.index += 1
        return turn


@pytest.fixture(scope="module")
def sample_url() -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), SampleHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    yield f"http://127.0.0.1:{port}/desk.html"
    httpd.shutdown()


def passing_script(url: str) -> str:
    return (
        "from playwright.sync_api import sync_playwright\n"
        "def test_target_page() -> None:\n"
        "    with sync_playwright() as playwright:\n"
        "        browser = playwright.chromium.launch(headless=True)\n"
        "        page = browser.new_page()\n"
        "        page.set_default_timeout(8000)\n"
        f"        page.goto({url!r}, wait_until='domcontentloaded')\n"
        "        page.get_by_role('button', name='Add to bag').wait_for(state='visible')\n"
        "        browser.close()\n"
        "if __name__ == '__main__':\n"
        "    test_target_page()\n"
    )


def test_a_target_page_that_cannot_be_opened_fails() -> None:
    examination = TestEngineer().examine("http://127.0.0.1:1/")

    assert examination.passed is False
    assert examination.attempts[0].failure.startswith("Could not open the Target page:")


def test_a_non_http_url_fails_without_opening_a_browser() -> None:
    examination = TestEngineer().examine("ftp://files.example/readme")

    assert examination.passed is False
    assert examination.attempts[0].failure == "Enter an http(s) URL."
    assert examination.script == ""


def test_examining_a_page_returns_a_passing_script_for_its_button_and_form_field(
    sample_url: str,
) -> None:
    examination = TestEngineer().examine(sample_url)

    assert examination.passed is True
    assert examination.attempts[0].passed is True
    assert "Add to bag" in examination.script
    assert "Quantity" in examination.script
    assert "field.fill('2')" in examination.script
    assert "submit" not in examination.script
    assert any(control.kind == "button" and control.name == "Add to bag" for control in examination.controls)
    assert any(
        control.kind == "form_field" and control.name == "Quantity" for control in examination.controls
    )
    assert "Studio desk" in examination.snapshot
    assert examination.screenshot_bytes > 100


def test_the_test_script_follows_one_flow_and_skips_a_cross_origin_link(sample_url: str) -> None:
    examination = TestEngineer().examine(sample_url)

    assert examination.passed is True
    assert any(
        control.kind == "navigation_link" and control.name == "Shipping" and control.destination == "Shipping"
        for control in examination.controls
    )
    assert examination.script.count(".click()") == 1
    assert "Shipping" in examination.script
    assert "example.com" not in examination.script


def test_a_failed_attempt_is_kept_and_a_later_attempt_can_pass(sample_url: str) -> None:
    bad = "import sys\nsys.exit('Missing button')\n"
    session = ScriptedSession(
        [
            ModelTurn("", (ToolCall("1", "write_test", {"source": bad}),)),
            ModelTurn("", (ToolCall("2", "write_test", {"source": passing_script(sample_url)}),)),
        ]
    )

    examination = TestEngineer(lambda: session).examine(sample_url)

    assert examination.attempts[0].passed is False
    assert "Missing button" in examination.attempts[0].failure
    assert examination.attempts[1].passed is True
    assert examination.passed is True
    assert examination.script == passing_script(sample_url)


def test_three_failing_attempts_stop_the_examination(sample_url: str) -> None:
    bad = "import sys\nsys.exit('still failing')\n"
    session = ScriptedSession(
        [ModelTurn("", (ToolCall(str(index), "write_test", {"source": bad}),)) for index in range(1, 5)]
    )

    examination = TestEngineer(lambda: session).examine(sample_url)

    assert examination.passed is False
    assert len(examination.attempts) == 3
    assert all("still failing" in attempt.failure for attempt in examination.attempts)
    assert session.index == 3


def test_the_model_observes_before_it_writes(sample_url: str) -> None:
    script = passing_script(sample_url)
    session = ScriptedSession(
        [
            ModelTurn("", (ToolCall("1", "observe", {}),)),
            ModelTurn("", (ToolCall("2", "write_test", {"source": script}),)),
        ]
    )

    examination = TestEngineer(lambda: session).examine(sample_url)

    assert examination.passed is True
    assert examination.script == script
    payload = json.loads(session.results[0][0][1])
    assert payload["heading"] == "Studio desk"
    assert "Studio desk" in payload["snapshot"]
    assert payload["screenshot_bytes"] > 100
    assert payload["screenshot_base64"]


def test_an_observation_picture_is_sent_with_the_words() -> None:
    payload = json.dumps(
        {
            "heading": "Studio desk",
            "snapshot": "Studio desk",
            "screenshot_base64": "aaaa",
            "screenshot_bytes": 4,
        }
    )

    messages = tool_followups("obs-1", payload)

    assert "aaaa" not in str(messages[0]["content"])
    assert "Studio desk" in str(messages[0]["content"])
    content = messages[1]["content"]
    assert isinstance(content, list)
    assert content[1]["image_url"]["url"] == "data:image/png;base64,aaaa"


def test_empty_url_is_rejected() -> None:
    client = TestClient(create_app(TestEngineer()))

    response = client.post("/examinations", json={"url": "  "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Enter a URL."


def test_page_offers_the_sample_target_page() -> None:
    client = TestClient(create_app(TestEngineer()))

    response = client.get("/")

    assert response.status_code == 200
    assert "/sample/desk.html" in response.text
    assert "Examine" in response.text


@pytest.fixture(scope="module")
def app_url() -> Iterator[str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = uvicorn.Server(
        uvicorn.Config(create_app(TestEngineer()), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    url = f"http://127.0.0.1:{port}"
    while time.time() < deadline:
        try:
            httpx.get(url, timeout=0.5)
            break
        except httpx.HTTPError:
            time.sleep(0.05)
    else:
        raise RuntimeError("The page did not start.")
    yield url
    server.should_exit = True
    thread.join(timeout=5)


def test_posting_the_sample_url_returns_a_passing_report(app_url: str) -> None:
    response = httpx.post(
        f"{app_url}/examinations",
        json={"url": f"{app_url}/sample/desk.html"},
        timeout=60,
    )

    body = response.json()
    assert response.status_code == 200
    assert body["passed"] is True
    assert "Add to bag" in body["script"]
    assert "Quantity" in body["script"]
    assert any(control["name"] == "Shipping" for control in body["controls"])
    assert body["attempts"][0]["passed"] is True
