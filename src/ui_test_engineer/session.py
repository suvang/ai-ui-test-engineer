import json
from dataclasses import dataclass
from typing import Any, cast

from openai.types.chat import ChatCompletionMessageFunctionToolCall

from ui_test_engineer.script import render_from_observation


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class ModelTurn:
    text: str
    tool_calls: tuple[ToolCall, ...]


class ToolSession:
    def start(self, system: str, user: str, tools: list[dict[str, object]]) -> ModelTurn:
        raise NotImplementedError

    def resume(self, results: list[tuple[ToolCall, str]]) -> ModelTurn:
        raise NotImplementedError


SYSTEM = (
    "You examine one Target page. Call observe before you write a Test script. "
    "Then call write_test with a complete Python Playwright script that uses sync_playwright, "
    "launches headless chromium, opens the URL, and exits 0 when the checks pass. "
    "Wait until the heading and each Button are visible, and do not press a Button. "
    "Fill each Form field with 2 and check that value. Do not submit. "
    "Click at most the one Navigation link and check its destination heading. "
    "Ignore cross-origin links. "
    "If the Run fails, call write_test again with a fix. "
    "Do not invent a Control that was not in the Observation."
)

TOOLS: list[dict[str, object]] = [
    {
        "name": "observe",
        "description": "Open the Target page and return the Observation: heading, words, Controls, and a picture.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "write_test",
        "description": "Provide the full Python Playwright Test script. The Examination will Run it.",
        "parameters": {
            "type": "object",
            "properties": {"source": {"type": "string"}},
            "required": ["source"],
            "additionalProperties": False,
        },
    },
]


class LocalSession(ToolSession):
    def __init__(self) -> None:
        self._payload: dict[str, object] | None = None
        self._dropped: set[str] = set()
        self._writes = 0

    def start(self, system: str, user: str, tools: list[dict[str, object]]) -> ModelTurn:
        return ModelTurn("", (ToolCall("observe-1", "observe", {}),))

    def resume(self, results: list[tuple[ToolCall, str]]) -> ModelTurn:
        call, payload = results[-1]
        if call.name == "observe":
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                self._payload = {str(key): value for key, value in parsed.items()}
            return self._write()
        if call.name == "write_test" and payload != "passed" and self._payload is not None:
            self._drop_named(payload)
            return self._write()
        return ModelTurn("passed" if payload == "passed" else "", ())

    def _write(self) -> ModelTurn:
        self._writes += 1
        source = render_from_observation(self._payload or {}, self._dropped)
        return ModelTurn(
            "",
            (ToolCall(f"write-{self._writes}", "write_test", {"source": source}),),
        )

    def _drop_named(self, failure: str) -> None:
        if self._payload is None:
            return
        raw = self._payload.get("controls")
        names: list[str] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    names.append(item["name"])
        for name in names:
            if name in failure and name not in self._dropped:
                self._dropped.add(name)
                return


def tool_followups(call_id: str, payload: str) -> list[dict[str, object]]:
    text, image = _split_image(payload)
    messages: list[dict[str, object]] = [
        {"role": "tool", "tool_call_id": call_id, "content": text}
    ]
    if image:
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Picture of the page from the Observation."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image}"},
                    },
                ],
            }
        )
    return messages


def _split_image(payload: str) -> tuple[str, str]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return payload, ""
    if not isinstance(parsed, dict):
        return payload, ""
    image = parsed.pop("screenshot_base64", "")
    if not isinstance(image, str):
        image = ""
    return json.dumps(parsed), image


class OpenAIToolSession(ToolSession):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._messages: list[Any] = []

    def start(self, system: str, user: str, tools: list[dict[str, object]]) -> ModelTurn:
        self._messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self._invoke()

    def resume(self, results: list[tuple[ToolCall, str]]) -> ModelTurn:
        for call, payload in results:
            self._messages.extend(tool_followups(call.id, payload))
        return self._invoke()

    def _invoke(self) -> ModelTurn:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=self._messages,
            tools=cast(Any, _openai_tools()),
        )
        message = response.choices[0].message
        self._messages.append(message.model_dump(exclude_none=True))
        calls: list[ToolCall] = []
        for call in message.tool_calls or []:
            if not isinstance(call, ChatCompletionMessageFunctionToolCall):
                continue
            parsed = json.loads(call.function.arguments or "{}")
            arguments = parsed if isinstance(parsed, dict) else {}
            calls.append(
                ToolCall(
                    call.id,
                    call.function.name,
                    {str(key): value for key, value in arguments.items()},
                )
            )
        return ModelTurn(message.content or "", tuple(calls))


def _openai_tools() -> list[dict[str, object]]:
    tools: list[dict[str, object]] = []
    for tool in TOOLS:
        tools.append({"type": "function", "function": tool})
    return tools
