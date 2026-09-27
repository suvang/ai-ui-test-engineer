from dataclasses import dataclass
from typing import Literal


ControlKind = Literal["button", "form_field", "navigation_link"]


@dataclass(frozen=True)
class Control:
    kind: ControlKind
    name: str
    destination: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "name": self.name, "destination": self.destination}


@dataclass(frozen=True)
class Attempt:
    script: str
    passed: bool
    failure: str


@dataclass(frozen=True)
class Examination:
    url: str
    passed: bool
    script: str
    controls: tuple[Control, ...]
    attempts: tuple[Attempt, ...]
    snapshot: str
    screenshot_bytes: int
