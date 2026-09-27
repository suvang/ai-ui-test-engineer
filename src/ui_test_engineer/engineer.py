from collections.abc import Callable
from urllib.parse import urlparse

from ui_test_engineer.explore import explore
from ui_test_engineer.runner import run_script
from ui_test_engineer.session import SYSTEM, TOOLS, LocalSession, ToolCall, ToolSession
from ui_test_engineer.types import Attempt, Control, Examination

MAX_ATTEMPTS = 3
MAX_TOOL_TURNS = 8


class TestEngineer:
    __test__ = False

    def __init__(self, session_factory: Callable[[], ToolSession] | None = None) -> None:
        self._session_factory = session_factory or (lambda: LocalSession())

    def examine(self, url: str) -> Examination:
        if not _http_url(url):
            failure = "Enter an http(s) URL."
            return Examination(url, False, "", (), (Attempt("", False, failure),), "", 0)
        session = self._session_factory()
        turn = session.start(SYSTEM, f"Examine this Target page: {url}", TOOLS)
        attempts: list[Attempt] = []
        controls: tuple[Control, ...] = ()
        snapshot = ""
        screenshot_bytes = 0
        script = ""
        for _ in range(MAX_TOOL_TURNS):
            if not turn.tool_calls:
                break
            results: list[tuple[ToolCall, str]] = []
            stop = False
            for call in turn.tool_calls:
                if call.name == "observe":
                    try:
                        observation = explore(url)
                    except Exception as error:
                        open_failure = f"Could not open the Target page: {error}"
                        attempts.append(Attempt("", False, open_failure))
                        stop = True
                        results.append((call, open_failure))
                        break
                    controls = observation.controls
                    snapshot = observation.snapshot
                    screenshot_bytes = len(observation.screenshot)
                    results.append((call, observation.payload_json()))
                elif call.name == "write_test":
                    source = call.arguments.get("source", "")
                    script = source if isinstance(source, str) else ""
                    run_failure = run_script(script)
                    attempts.append(Attempt(script, run_failure is None, run_failure or ""))
                    results.append((call, "passed" if run_failure is None else run_failure))
                    if run_failure is None or len(attempts) >= MAX_ATTEMPTS:
                        stop = True
                else:
                    results.append((call, "Unknown tool."))
            if stop or not results:
                break
            turn = session.resume(results)
        passed = bool(attempts) and attempts[-1].passed
        return Examination(
            url,
            passed,
            script,
            controls,
            tuple(attempts),
            snapshot,
            screenshot_bytes,
        )


def _http_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
