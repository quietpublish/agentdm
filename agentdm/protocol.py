"""Validate incoming wire shape before dispatch can mutate a store.

Owner: JSON-RPC/MCP envelope validation, not tool policy or mailbox state.
Inputs: one decoded text line. Outputs: a typed message, no-op, or a bounded
protocol error with a safe request ID. No I/O or host dependencies. Notifications
never gain request authority; only cancellation is handled by this server.
"""
from dataclasses import dataclass
import json
from typing import Any, Optional, Union

RequestId = Union[str, int]


def valid_request_id(value):
    return isinstance(value, str) or (isinstance(value, int) and not isinstance(value, bool))


@dataclass(frozen=True)
class Incoming:
    method: str
    request_id: Optional[RequestId]
    params: dict


class InvalidMessage(ValueError):
    def __init__(self, request_id, message, code=-32600):
        super().__init__(message)
        self.request_id = request_id
        self.code = code


def decode_message(line: str) -> Optional[Incoming]:
    try:
        raw = json.loads(line)
    except (json.JSONDecodeError, ValueError, RecursionError):
        return None
    if not isinstance(raw, dict):
        return None
    supplied_id: Any = raw.get("id")
    rid = supplied_id if valid_request_id(supplied_id) else None
    if raw.get("jsonrpc") != "2.0" or not isinstance(raw.get("method"), str):
        raise InvalidMessage(rid, "invalid request envelope")
    method = raw["method"]
    if "id" in raw and rid is None:
        return None
    # Tool calls, initialization and ping are requests, not notifications.
    if rid is None and method != "notifications/cancelled":
        return None
    params = raw.get("params", {})
    if not isinstance(params, dict):
        raise InvalidMessage(rid, "params must be an object", -32602)
    if method == "tools/call":
        if not isinstance(params.get("name"), str) or not params["name"]:
            raise InvalidMessage(rid, "tool name must be a nonempty string", -32602)
        if not isinstance(params.get("arguments", {}), dict):
            raise InvalidMessage(rid, "tool arguments must be an object", -32602)
    return Incoming(method, rid, params)
