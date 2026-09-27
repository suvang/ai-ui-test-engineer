# UI test engineer

Enter a Target page URL. The Examination opens it with Playwright, records the Buttons, Form fields, and one Navigation link, writes a Python Playwright Test script, Runs it, and reports Failures. A later Attempt can replace a failing Test script. With `OPENAI_API_KEY` set, a model calls the observe and write tools and sees a picture of the page. Without a key, the same tools run from the Observation alone.

Open http://127.0.0.1:8030 after the server starts. The page fills in the sample Target page.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
cp .env.example .env
uvicorn ui_test_engineer.asgi:app --app-dir src --port 8030
```

Without `OPENAI_API_KEY`, the local planner writes the Test script. With a key, OpenAI does. Restart the server after changing `.env`.

The Test script is executed on this machine. Do not point an Examination at a page you are not willing to open in a browser.
