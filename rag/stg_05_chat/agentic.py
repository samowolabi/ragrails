"""Tool-loop chat generation.

This module owns the agentic generation path: the model can ask to call tools,
the application validates and optionally confirms those tool calls, and the
tool outputs are sent back to the model until it returns a final answer.

Provider-specific tool schema formatting does not live here. `TOOL_SPECS` are
provider-neutral definitions; each LLM provider converts them into its own API
format inside `models/llm/providers/*`.

Example:
    response = generate_agentic(
        query="Calculate a payout fee",
        results=retrieved_chunks,
        llm=session.llm,
        config=session.chat_config,
        history=session.history,
        confirm_fn=ui.confirm_tool_call,
    )

    # The response contains the final model answer after zero or more tool calls.
    session.history = response.history
"""

from typing import Callable

from models.llm import usage_logger
from models.llm.base import (
    AssistantToolCallMessage,
    ChatMessage,
    History,
    LLMProvider,
    ToolLoopMessage,
    ToolResultMessage,
)
from models.vector_db.base import SearchResult

from .config import ChatConfig
from .generator import TOOL_RULES, finish_response, prepare_prompt
from .responses import GeneratorResponse
from .tools import TOOL_SPECS, TOOLS_REQUIRING_CONFIRM, run_tool, validate_tool_call

MAX_TOOL_ITERATIONS = 5


def generate_agentic(
    query: str,
    results: list[SearchResult],
    llm: LLMProvider,
    config: ChatConfig | None = None,
    history: History | None = None,
    confirm_fn: Callable[[str, dict], bool] | None = None,
) -> GeneratorResponse:
    """Run a tool-calling loop until the model returns a final answer.

    Flow:
        1. Build the same RAG prompt used by plain generation.
        2. Add tool-specific behavior rules to the system prompt.
        3. Send provider-neutral tool definitions to the active LLM provider.
        4. If the model requests tools, validate every call before execution.
        5. Ask for user confirmation when a tool is marked as requiring it.
        6. Append tool results to the message list and continue.
        7. Stop when the model returns text without tool calls.

    Invalid calls are not executed. Instead, a synthetic tool result explaining
    the validation error is appended so the model can recover by asking the user
    for missing fields or producing a non-tool answer.

    Example:
        response = generate_agentic(
            "What is the payout fee for NGN 100?",
            results,
            llm=session.llm,
            confirm_fn=ui.confirm_tool_call,
        )
        assert isinstance(response.answer, str)
    """
    cfg = config or ChatConfig()
    filtered, system, user = prepare_prompt(query, results, cfg)
    system += TOOL_RULES

    # Keep the tool loop provider-neutral. Provider adapters are responsible for
    # turning these text/tool messages into their own wire formats.
    messages: list[ToolLoopMessage] = [
        ChatMessage(role=msg["role"], content=msg["content"])
        for msg in (history or [])
    ]
    messages.append(ChatMessage(role="user", content=user))

    response = None
    for _ in range(MAX_TOOL_ITERATIONS):
        response = llm.complete_with_tools(messages=messages, system=system, tools=TOOL_SPECS)
        usage_logger.log(response, action="agentic_generate")

        if not response.tool_calls:
            break

        # Preserve the assistant tool-call message so provider APIs can link
        # subsequent tool results back to the exact calls they answer.
        messages.append(AssistantToolCallMessage(content=response.text, tool_calls=response.tool_calls))

        for tc in response.tool_calls:
            # Validation happens before confirmation so the user is never asked
            # to approve an incomplete or unsafe call.
            validation_error = validate_tool_call(tc.name, tc.arguments)
            if validation_error:
                messages.append(ToolResultMessage(
                    tool_call_id=tc.id,
                    content=f"Tool call rejected before execution: {validation_error}",
                ))
                continue

            if tc.name in TOOLS_REQUIRING_CONFIRM and confirm_fn is not None:
                # Side-effecting tools, such as live API calls, pause here for
                # explicit user approval.
                if not confirm_fn(tc.name, tc.arguments):
                    messages.append(ToolResultMessage(
                        tool_call_id=tc.id,
                        content="User declined. Do not retry — inform the user the action was cancelled.",
                    ))
                    continue

            print(f"  [tool] {tc.name}({tc.arguments})")
            messages.append(ToolResultMessage(tool_call_id=tc.id, content=run_tool(tc.name, tc.arguments)))

    answer = (response.text or "") if response else ""
    return finish_response(query, answer, history, filtered)
