from dataclasses import dataclass
from typing import Literal


ControlKind = Literal["button", "form_field", "navigation_link"]
Navigation = Literal["passed", "failed", "stayed", "missed"]


@dataclass(frozen=True)
class Control:
    kind: ControlKind
    name: str
    destination: str = ""
    landed_url: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "name": self.name,
            "destination": self.destination,
            "landed_url": self.landed_url,
        }


@dataclass(frozen=True)
class ApiCall:
    name: str
    method: str
    url: str
    status: int | None
    ok: bool
    detail: str
    resource: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "method": self.method,
            "url": self.url,
            "status": self.status,
            "ok": self.ok,
            "detail": self.detail,
            "resource": self.resource,
        }


@dataclass(frozen=True)
class Finding:
    name: str
    kind: str
    navigation: Navigation
    destination: str
    action: str
    detail: str
    calls: tuple[ApiCall, ...]
    passed: bool
    screenshot: str
    network: tuple[ApiCall, ...] = ()
    network_screenshot: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "navigation": self.navigation,
            "destination": self.destination,
            "action": self.action,
            "detail": self.detail,
            "passed": self.passed,
            "screenshot": self.screenshot,
            "network_screenshot": self.network_screenshot,
            "calls": [call.as_dict() for call in self.calls],
            "network": [call.as_dict() for call in self.network],
        }


@dataclass(frozen=True)
class Examination:
    url: str
    passed: bool
    findings: tuple[Finding, ...]
    page_calls: tuple[ApiCall, ...]
    snapshot: str
    page_screenshot: str
    detail: str = ""
    page_network_screenshot: str = ""
