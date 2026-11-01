from urllib.parse import urlparse

from ui_test_engineer.audit import audit
from ui_test_engineer.narrator import Narrator
from ui_test_engineer.types import Examination


class TestEngineer:
    __test__ = False

    def __init__(self, narrator: Narrator | None = None) -> None:
        self._narrator = narrator

    def examine(self, url: str) -> Examination:
        if not _http_url(url):
            return Examination(url, False, (), (), "", "", "Enter an http(s) URL.")
        try:
            findings, page_calls, snapshot, page_screenshot, page_network_screenshot = audit(url)
        except Exception as error:
            detail = f"Could not open the Target page: {error}"
            return Examination(url, False, (), (), "", "", detail)
        if self._narrator is not None:
            findings = self._narrator(findings)
        passed = all(finding.passed for finding in findings) and all(call.ok for call in page_calls)
        return Examination(
            url,
            passed,
            findings,
            page_calls,
            snapshot,
            page_screenshot,
            page_network_screenshot=page_network_screenshot,
        )


def _http_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
