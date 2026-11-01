# UI test engineer

Enter a page URL. Playwright opens it, then clicks every visible link and button. The report has two parts: API calls that failed or succeeded just by opening that page, and each call to action with its own navigation result and the API calls that click made. A login check or a prefetch on the destination page stays out of the click. With `OPENAI_API_KEY` set, a model rewrites the “what it did” line. Pass or fail still comes from Playwright.

Open http://127.0.0.1:8030 after the server starts. The page fills in the sample page.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
cp .env.example .env
uvicorn ui_test_engineer.asgi:app --app-dir src --port 8030
```

Restart the server after changing `.env`.

The examination clicks the page you name, including buttons that call APIs. Do not point it at a page you are not willing to click through.
