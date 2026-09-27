import subprocess
import sys
import tempfile
from pathlib import Path


def run_script(source: str) -> str | None:
    if not source.strip():
        return "The Test script was empty."
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test_target_page.py"
        path.write_text(source, encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return "The Run timed out."
    if completed.returncode == 0:
        return None
    detail = f"{completed.stdout}\n{completed.stderr}".strip()
    return detail[-2000:] or f"The Run failed with exit code {completed.returncode}."
