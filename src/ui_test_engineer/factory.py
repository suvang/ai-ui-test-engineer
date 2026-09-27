import os
from collections.abc import Mapping

from ui_test_engineer.engineer import TestEngineer
from ui_test_engineer.session import LocalSession, OpenAIToolSession


def build_engineer(env: Mapping[str, str] | None = None) -> TestEngineer:
    if env is None:
        from dotenv import load_dotenv

        load_dotenv()
        settings: Mapping[str, str] = os.environ
    else:
        settings = env
    api_key = settings.get("OPENAI_API_KEY") or ""
    if api_key:
        return TestEngineer(lambda: OpenAIToolSession(api_key))
    return TestEngineer(lambda: LocalSession())
