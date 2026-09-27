from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ui_test_engineer.engineer import TestEngineer
from ui_test_engineer.factory import build_engineer
from ui_test_engineer.types import Examination

PAGE = Path(__file__).parent / "static" / "index.html"
SAMPLE = Path(__file__).parent / "static" / "sample"


class ExamineBody(BaseModel):
    url: str


def create_app(engineer: TestEngineer | None = None) -> FastAPI:
    app = FastAPI(title="UI test engineer")
    service = engineer if engineer is not None else build_engineer()
    app.mount("/sample", StaticFiles(directory=SAMPLE), name="sample")

    @app.get("/")
    def home() -> FileResponse:
        return FileResponse(PAGE)

    @app.post("/examinations")
    def examinations(body: ExamineBody) -> dict[str, object]:
        if not body.url.strip():
            raise HTTPException(status_code=400, detail="Enter a URL.")
        return _examination_json(service.examine(body.url.strip()))

    return app


def _examination_json(examination: Examination) -> dict[str, object]:
    return {
        "url": examination.url,
        "passed": examination.passed,
        "script": examination.script,
        "snapshot": examination.snapshot,
        "screenshot_bytes": examination.screenshot_bytes,
        "controls": [control.as_dict() for control in examination.controls],
        "attempts": [
            {"passed": attempt.passed, "failure": attempt.failure, "script": attempt.script}
            for attempt in examination.attempts
        ],
    }
