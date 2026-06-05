"""
Token usage logger. Appends one JSON record per LLM call to files/output/token_usage.jsonl.

Each record: timestamp, action, provider, model, input_tokens, output_tokens, cost_usd.
"""

import json
import os
from datetime import datetime, timezone

from .base import LLMResponse, LLMToolResponse
from .registry import get as get_model

LOG_PATH = "files/output/token_usage.jsonl"


def _cost(model: str, input_tokens: int, output_tokens: int) -> float:
    info = get_model(model)
    if info is None:
        return 0.0
    return (input_tokens * info.input_price + output_tokens * info.output_price) / 1_000_000


def log(response: LLMResponse | LLMToolResponse, action: str, log_path: str = LOG_PATH) -> None:
    """Append a usage record for one LLM call.

    Example:
        log(response, action="query_rewrite")
        # → appends {"action": "query_rewrite", "cost_usd": "0.0000042", ...} to token_usage.jsonl
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    cost = _cost(response.model, response.input_tokens, response.output_tokens)
    record = {
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "action":        action,
        "provider":      response.provider,
        "model":         response.model,
        "input_tokens":  response.input_tokens,
        "output_tokens": response.output_tokens,
        "total_tokens":  response.input_tokens + response.output_tokens,
        "cost_usd":      f"{cost:.7f}",
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"  \033[2m[{action}] tokens: {record['input_tokens']} in / {record['output_tokens']} out  cost: ${record['cost_usd']}\033[0m")


def summary(log_path: str = LOG_PATH) -> None:
    """Print total tokens and cost grouped by action.

    Example:
        summary()
        # → prints a table of calls, tokens, and cost per action
    """
    if not os.path.exists(log_path):
        print("No usage log found.")
        return

    records = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if not records:
        print("No usage records found.")
        return

    total_in   = sum(r["input_tokens"] for r in records)
    total_out  = sum(r["output_tokens"] for r in records)
    total_cost = sum(float(r["cost_usd"]) for r in records)

    by_action: dict[str, dict] = {}
    for r in records:
        a = r["action"]
        if a not in by_action:
            by_action[a] = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
        by_action[a]["calls"]         += 1
        by_action[a]["input_tokens"]  += r["input_tokens"]
        by_action[a]["output_tokens"] += r["output_tokens"]
        by_action[a]["cost_usd"]      += float(r["cost_usd"])

    w = 60
    print(f"\n{'─' * w}")
    print(f"  TOKEN USAGE SUMMARY  ({len(records)} calls)")
    print(f"{'─' * w}")
    for action, s in by_action.items():
        print(f"  {action:<22} {s['calls']:>4} calls  "
              f"{s['input_tokens']:>7} in  {s['output_tokens']:>7} out  ${s['cost_usd']:.4f}")
    print(f"{'─' * w}")
    print(f"  {'TOTAL':<22} {len(records):>4} calls  "
          f"{total_in:>7} in  {total_out:>7} out  ${total_cost:.4f}")
    print(f"{'─' * w}\n")
