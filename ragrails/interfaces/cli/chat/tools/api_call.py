"""api_call tool implementation."""

import json

import httpx

from .base import ToolSpec

def run_api_call(
    method: str,
    url: str,
    headers: dict | None = None,
    params: dict | None = None,
    body: dict | None = None,
) -> str:
    """Make a synchronous HTTP request and return the response as a formatted string."""
    try:
        with httpx.Client(headers=headers or {}, timeout=30.0) as client:
            resp = client.request(method.upper(), url, params=params or {}, json=body)
            resp.raise_for_status()
            try:
                return json.dumps(resp.json(), indent=2)
            except Exception:
                return resp.text
    except httpx.HTTPStatusError as e:
        return f"HTTP {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"Request error: {e}"


def validate_api_call(arguments: dict) -> str | None:
    missing = [
        key for key in ("method", "url", "headers", "params", "body")
        if key not in arguments
    ]
    if missing:
        return (
            "api_call is missing required argument(s): "
            f"{', '.join(missing)}. Provide method, url, headers, params, and body explicitly; "
            "use {} only for params/body/headers that are genuinely empty."
        )

    method = str(arguments.get("method", "")).upper()
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        return "api_call method must be one of GET, POST, PUT, PATCH, DELETE."

    if not arguments.get("url"):
        return "api_call requires a non-empty url."

    for key in ("headers", "params", "body"):
        if not isinstance(arguments.get(key), dict):
            return f"api_call {key} must be an object."

    if method in {"POST", "PUT", "PATCH"} and not arguments["body"]:
        return f"api_call {method} requests require a non-empty body."

    auth = arguments["headers"].get("Authorization", "")
    if isinstance(auth, str) and "<" in auth and ">" in auth:
        return "api_call Authorization header contains a placeholder. Ask the user for the real token."

    return None


API_CALL_TOOL = ToolSpec(
    name="api_call",
    description=(
        "Make a live HTTP request. Use this to execute API calls the user requests — "
        "e.g. initiating a transfer, fetching account details, creating a resource. "
        "Collect ALL required parameters from the user before calling. "
        "Always put authentication in headers as {\"Authorization\": \"Bearer <token>\"} "
        "and request body fields in the body object. "
        "Use exact values the user provided — never placeholders like YOUR_SECRET_KEY."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                "description": "HTTP method.",
            },
            "url": {
                "type": "string",
                "description": "Full request URL.",
            },
            "headers": {
                "type": "object",
                "description": "Request headers, e.g. Authorization, Content-Type. Use {} only when no headers are required.",
                "additionalProperties": {"type": "string"},
            },
            "params": {
                "type": "object",
                "description": "URL query parameters. Use {} when there are none.",
                "additionalProperties": {"type": "string"},
            },
            "body": {
                "type": "object",
                "description": "JSON request body for POST / PUT / PATCH. Use {} only when no body is required.",
                "additionalProperties": True,
            },
        },
        "required": ["method", "url", "headers", "params", "body"],
        "additionalProperties": False,
    },
    handler=lambda arguments: run_api_call(
        method=arguments["method"],
        url=arguments["url"],
        headers=arguments.get("headers"),
        params=arguments.get("params"),
        body=arguments.get("body") or arguments.get("data"),
    ),
    validator=validate_api_call,
    requires_confirmation=True,
)
