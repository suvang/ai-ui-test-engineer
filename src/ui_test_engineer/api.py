from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
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

    @app.get("/demo/rendered-500")
    def rendered_500() -> HTMLResponse:
        html = (
            "<h1>Explore</h1><p>The explore page rendered with its articles "
            "and categories still visible to the reader.</p>"
        )
        return HTMLResponse(html, status_code=500)

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
        "detail": examination.detail,
        "snapshot": examination.snapshot,
        "page_screenshot": examination.page_screenshot,
        "page_network_screenshot": examination.page_network_screenshot,
        "page_calls": [call.as_dict() for call in examination.page_calls],
        "findings": [finding.as_dict() for finding in examination.findings],
    }
