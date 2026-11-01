import json
from collections.abc import Callable

from ui_test_engineer.types import Finding

Narrator = Callable[[tuple[Finding, ...]], tuple[Finding, ...]]


def phrase_findings(api_key: str, findings: tuple[Finding, ...]) -> tuple[Finding, ...]:
    if not findings:
        return findings
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        payload = [
            {
                "name": finding.name,
                "kind": finding.kind,
                "passed": finding.passed,
                "action": finding.action,
                "detail": finding.detail,
                "calls": [call.as_dict() for call in finding.calls],
            }
            for finding in findings
        ]
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You describe what each call to action did, in one plain sentence. "
                        "Use only the action, detail, and calls you are given. "
                        "Do not invent a destination or an API. "
                        "Do not change whether it passed. "
                        'Return {"items": [{"name": "...", "action": "..."}]} in the same order.'
                    ),
                },
                {"role": "user", "content": json.dumps(payload)},
            ],
        )
        content = response.choices[0].message.content or ""
        parsed = json.loads(content)
        items = parsed.get("items") if isinstance(parsed, dict) else None
        if not isinstance(items, list) or len(items) != len(findings):
            return findings
        updated: list[Finding] = []
        for finding, item in zip(findings, items, strict=True):
            action = item.get("action") if isinstance(item, dict) else None
            if not isinstance(action, str) or not action.strip():
                updated.append(finding)
                continue
            updated.append(
                Finding(
                    finding.name,
                    finding.kind,
                    finding.navigation,
                    finding.destination,
                    action.strip(),
                    finding.detail,
                    finding.calls,
                    finding.passed,
                    finding.screenshot,
                    finding.network,
                    finding.network_screenshot,
                )
            )
        return tuple(updated)
    except Exception:
        return findings
