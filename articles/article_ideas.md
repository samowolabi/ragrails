# Article Ideas

Article angles drawn from what this codebase actually demonstrates — not generic
RAG content. Each entry calls out concrete files/decisions you can show.

## Architecture & decisions you can show with real diffs

1. **Why I separated `generate` from `generate_agentic`** — design tension between
   flag-driven and function-driven APIs. Receipts: the conversation where stream
   collapsed into a flag but agentic stayed separate. Files:
   `rag/stg_05_chat/generator.py`, `rag/stg_05_chat/agentic.py`.

2. **A provider-neutral tool-calling abstraction in 200 lines** — show
   `ChatMessage` / `AssistantToolCallMessage` / `ToolResultMessage` and how
   OpenAI vs Anthropic adapters consume them. Single most reusable pattern in
   the repo. Files: `models/llm/base.py`, `models/llm/providers/`.

3. **Single source of truth for LLM models: a registry pattern** —
   `models/llm/registry.py` + per-provider modules. Common problem (model lists
   scattered everywhere), clean fix.

4. **Capability-aware model switching: when your model can't use tools** —
   `ensure_tool_model()`. Real bug it solves, real fallback logic, code small
   enough to fit in an article. File: `rag/stg_05_chat/model_control.py`.

## RAG mechanics with measurable claims

5. **Why your RAG needs two stages, not one** — bi-encoder retrieve +
   cross-encoder rerank. Show `min_retrieval_score` / `min_rerank_score`
   thresholds, why they exist, what happens when you remove them. Files:
   `rag/stg_04_retriever/retriever.py`, `rag/stg_05_chat/config.py`.

6. **Query rewriting saved my RAG from broken follow-ups** — pronoun resolution
   ("do they support NGN?") → `session_context` → rewriter. Before/after
   retrieval results. Files: `rag/stg_04_retriever/query_rewriter.py`,
   `rag/stg_05_chat/pipeline.py`.

7. **Background-thread summarization: keeping conversation context cheap** —
   `session_context` + `pending_summary`. Economics: instead of feeding full
   history to the rewriter every turn, summarize. Show the token math. File:
   `rag/stg_05_chat/history.py`.

## Engineering posts (the kind that actually rank)

8. **I refactored my RAG chat module twice and here's what I learned** —
   journey from 180-line `__main__.py` to `ChatSession` + `pipeline.run_turn()`.
   Diffs, why it was bad, why it's better. People love before/after.

9. **Slash commands in a CLI chat: `/model`, `/stream`, `/tools`, `/usage`** —
   small UX upgrade most CLI RAGs skip. Clean pattern. File:
   `rag/stg_05_chat/control/`.

10. **Tool calling with user confirmation: don't trust the LLM with money** —
    `requires_confirmation` flag + `confirm_fn` gate. Frame around BudPay's API:
    LLM wants to call payout, here's how the user approves. Strong concrete
    example. Files: `rag/stg_05_chat/tools/`, `rag/stg_05_chat/ui.py`.

11. **Validate tool calls before you confirm them** — `validate_tool_call()` →
    synthetic tool-result feedback loop. Why this is better than letting the LLM
    fail at execution time. File: `rag/stg_05_chat/agentic.py`.

## Honest / contrarian angles (these get traction)

12. **Agentic RAG vs fixed RAG: when do you actually need tools?** — both paths
    coexist in this codebase. Pros/cons, cost/latency comparison. Most articles
    cheerlead agents; an honest comparison stands out.

13. **My RAG works. I have no idea how well.** — the missing-evals confession.
    Vulnerable, true, ends with "here's what I'm building next." High
    engagement angle.

14. **What `gpt-4o-mini` quietly fails at in tool calling** — real story: `data`
    vs `body`, model dropping headers, the param-collection prompt rules.
    Specific, debuggable, useful to readers.

15. **Why I dropped `agentic_model` after building it** — over-engineering
    retrospective. Built the dual-model split, then realized `/model` makes it
    redundant. Killing your own feature is the most honest engineering content
    there is.

## Series / longform

16. **Building a production-shape RAG from scratch** — multi-part:
    ingestion → chunking → embedding → retrieval → chat → tool calling → eval.
    Each post is one `stg_NN_*` directory. Numbered packages give the spine for
    free.

17. **Reading the RAG: a code tour** — single long post walking through the
    directory tree, explaining why each module exists. Lower effort, high
    reference value.

## Picks ranked by effort × reach

- **High reach, low effort**: 8 (refactor journey), 13 (no evals confession),
  14 (model failures with receipts).
- **High reach, medium effort**: 2 (provider-neutral tools), 12 (agentic vs
  fixed comparison).
- **High reach, high effort**: 16 (the series — but compounds).

Start with **#8** or **#14** — strongest narrative spine and the code is
already written.

## From Codex: New angles after the eval/debug/citation work

18. **Building a production-minded RAG pipeline from scratch** — walk through the
    full flow: ingestion, chunking, embedding, Qdrant retrieval, reranking, query
    rewriting, generation, chunk citations, and evals. This is the broad anchor
    article for the whole repo.

19. **Why your RAG needs an eval suite before you trust it** — use the OpenCode
    result as the concrete proof point: `97.4/100`, `36/36` retrieval hit,
    `34/36` top-1, `0.968` MRR, `36/36` valid citations. Explain golden JSONL
    files, expected source hints, required terms, MRR, citation checks, and the
    optional LLM judge.

20. **Chunk-level citations: fixing page-level source attribution in RAG** —
    show why page-level source lists are too vague, then explain `[C1]`, `[C2]`
    chunk labels, inline citations, source rendering, and invalid citation
    detection.

21. **Adding `/debug` to a RAG chatbot** — explain how the debug trace exposes
    original query, rewritten query, retrieved chunks, reranked chunks, thresholds,
    scores, generation mode, and chunks used in the prompt.

22. **Provider-agnostic LLM architecture for RAG apps** — cover OpenAI/Anthropic
    separation, `ModelInfo`, registry-driven dispatch, provider modules,
    streaming differences, and provider-specific tool adapters.

23. **Tool calling in RAG: why provider-neutral messages matter** — tell the
    story of leaking OpenAI-shaped `tool_calls` into the agent loop, then show the
    neutral `ChatMessage`, `AssistantToolCallMessage`, and `ToolResultMessage`
    abstraction.

24. **Designing slash commands for a local RAG agent** — cover `/model`,
    `/stream`, `/usage`, `/tools`, and `/debug`; explain why commands should be
    handled locally and never sent to the LLM or stored in chat history.

25. **When RAG query rewriting goes wrong** — use the OpenCode/BudPay persona
    leak as the real bug. Explain how answer persona polluted the rewrite context
    and why eval runners need a separate `--rewrite-context`.

26. **Streaming, tools, and model capabilities in a RAG chat system** — explain
    why not every model supports tools, why streaming and multi-step tool loops
    need different handling, and how capability-aware model switching works.

27. **Building a golden dataset from your vector database** — show how to inspect
    Qdrant chunks and generate eval cases for BudPay and OpenCode collections
    using `expected_sources` and `required_terms`.


## From Codex: Suggested updated series

1. **Building the RAG pipeline** — staged folders, ingestion, chunking,
   embeddings, retrieval, reranking, generation.
2. **Making RAG observable with `/debug`** — trace what the system actually did.
3. **Fixing citations with chunk-level sources** — move from page-level sources
   to `[C1]`-style evidence.
4. **Evaluating RAG quality with golden tests** — retrieval hit, top-1, MRR,
   required terms, citations, LLM judge.
5. **Making it agentic with tools and provider-agnostic LLMs** — safe tool calls,
   provider adapters, model capabilities.
