"""An Examination clicks every call to action and reports what each one did."""

import base64
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from ui_test_engineer.api import create_app
from ui_test_engineer.engineer import TestEngineer

PAGE = """<!DOCTYPE html>
<html>
<body>
  <h1>Shop</h1>
  <a href="/next">Shipping</a>
  <a href="/missing">Broken link</a>
  <a href="/crew">Join<br>us</a>
  <a href="/rendered">Explore Content</a>
  <button type="button" id="ok">Load items</button>
  <button type="button" id="bad">Load broken</button>
  <script>
    fetch("/api/health");
    document.getElementById("ok").onclick = () => {
      fetch("/api/items");
      fetch("/api/health");
      fetch("/next?_rsc=1");
    };
    document.getElementById("bad").onclick = () => fetch("/api/broken");
  </script>
</body>
</html>
"""


class ShopHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, "text/html", PAGE.encode())
        elif path == "/next":
            self._send(200, "text/html", b"<h1>Next</h1>")
        elif path == "/crew":
            self._send(200, "text/html", b"<h1>Crew</h1>")
        elif path == "/rendered":
            page = (
                b"<h1>Explore</h1><p>The explore page rendered with its articles "
                b"and categories still visible to the reader.</p>"
            )
            self._send(500, "text/html", page)
        elif path == "/api/items":
            self._send(200, "application/json", b'{"ok": true}')
        elif path == "/api/health":
            self._send(500, "application/json", b'{"error": "down"}')
        elif path == "/api/broken":
            self._send(500, "application/json", b'{"error": "nope"}')
        else:
            self._send(404, "text/html", b"missing")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def shop_url() -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), ShopHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    yield f"http://127.0.0.1:{port}/"
    httpd.shutdown()


def test_a_non_http_url_fails_without_opening_a_browser() -> None:
    examination = TestEngineer().examine("ftp://files.example/readme")

    assert examination.passed is False
    assert examination.detail == "Enter an http(s) URL."


def test_a_target_page_that_cannot_be_opened_fails() -> None:
    examination = TestEngineer().examine("http://127.0.0.1:1/")

    assert examination.passed is False
    assert examination.detail.startswith("Could not open the Target page:")


def test_each_call_to_action_is_reported(shop_url: str) -> None:
    examination = TestEngineer().examine(shop_url)
    by_name = {finding.name: finding for finding in examination.findings}

    assert set(by_name) == {
        "Shipping",
        "Broken link",
        "Join us",
        "Explore Content",
        "Load items",
        "Load broken",
    }
    assert examination.passed is False

    assert base64.b64decode(examination.page_screenshot).startswith(b"\x89PNG")
    assert base64.b64decode(examination.page_network_screenshot).startswith(b"\x89PNG")

    health = next(call for call in examination.page_calls if call.name == "/api/health")
    assert health.method == "GET"
    assert health.status == 500
    assert health.ok is False
    assert all(call.name != "/api/health" for finding in examination.findings for call in finding.calls)

    shipping = by_name["Shipping"]
    assert shipping.passed is True
    assert shipping.navigation == "passed"
    assert shipping.kind == "link"
    assert shipping.calls == ()
    assert "/next" in shipping.action
    assert shipping.network == ()
    assert shipping.network_screenshot == ""
    assert base64.b64decode(shipping.screenshot).startswith(b"\x89PNG")

    explore = by_name["Explore Content"]
    assert explore.passed is True
    assert explore.navigation == "passed"
    assert "The page rendered." in explore.action
    assert "Navigation" not in explore.detail
    rendered = next(call for call in explore.network if call.status == 500)
    assert rendered.method == "GET"
    assert rendered.url.endswith("/rendered")
    assert base64.b64decode(explore.screenshot).startswith(b"\x89PNG")
    assert base64.b64decode(explore.network_screenshot).startswith(b"\x89PNG")

    joined = by_name["Join us"]
    assert joined.passed is True
    assert joined.navigation == "passed"
    assert "could not be clicked" not in joined.detail
    assert "/crew" in joined.action

    broken = by_name["Broken link"]
    assert broken.passed is False
    assert broken.navigation == "failed"
    assert broken.calls == ()
    assert "404" in broken.detail

    items = by_name["Load items"]
    assert items.passed is True
    assert items.navigation == "stayed"
    assert [call.name for call in items.calls] == ["/api/items"]
    assert items.calls[0].method == "GET"
    assert items.calls[0].ok is True

    failed = by_name["Load broken"]
    assert failed.passed is False
    assert failed.navigation == "stayed"
    call = next(item for item in failed.calls if item.name == "/api/broken")
    assert call.method == "GET"
    assert call.status == 500
    assert call.ok is False
    assert "/api/broken" in failed.detail
    assert base64.b64decode(failed.screenshot).startswith(b"\x89PNG")
    assert base64.b64decode(failed.network_screenshot).startswith(b"\x89PNG")


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
    assert "call to action" in response.text
    assert "Examine" in response.text
