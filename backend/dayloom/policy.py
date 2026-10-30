import hashlib
import json
from typing import Any


def action_digest(tool: str, payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        {"tool": tool, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def require_approval(tool: str, payload: dict[str, Any], approved_digest: str | None) -> None:
    if approved_digest is None or approved_digest != action_digest(tool, payload):
        raise ValueError("This exact action has not been approved.")
