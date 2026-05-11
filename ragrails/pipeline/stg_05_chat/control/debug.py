"""/debug — show the latest local RAG trace.

Usage:
    /debug

This command reads `session.debug_trace`, which is populated by `run_turn()`.
It does not call the LLM and does not enter conversation history.
"""

from ..session import ChatSession


def handle(args: str, session: ChatSession) -> None:
    """Print the latest RAG trace without calling an LLM."""
    if args.strip():
        print("  Usage: /debug")
        return

    trace = session.debug_trace
    if trace is None:
        print("  No RAG trace yet. Ask a question first, then run /debug.")
        return

    print("\n  ────────────────────────────────────────────────────────────")
    print("  RAG DEBUG")
    print("  ────────────────────────────────────────────────────────────")
    print(f"  query:      {trace.original_query}")
    if trace.rewritten_query and trace.rewritten_query != trace.original_query:
        print(f"  rewritten:  {trace.rewritten_query}")
    print(f"  model:      {trace.provider}/{trace.model}")
    print(f"  mode:       {trace.generation_mode or 'unknown'}")
    print(f"  stream:     {'on' if trace.stream else 'off'}")
    print(f"  tools:      {'on' if trace.tools_enabled else 'off'}")

    if trace.conversational:
        print("  retrieval:  skipped conversational turn")
        print("  ────────────────────────────────────────────────────────────\n")
        return

    print(f"  retrieve:   top_k={trace.retrieval_top_k}, candidates={trace.retrieval_candidate_k}")
    print(f"  thresholds: retrieval>={trace.min_retrieval_score:.4f}, rerank>={trace.min_rerank_score:.4f}")

    if trace.retrieval_error:
        print(f"  error:      {trace.retrieval_error}")
    elif trace.retrieval_skipped_reason:
        print(f"  skipped:    {trace.retrieval_skipped_reason}")

    _print_chunks("Retrieved", trace.candidates, score_kind="retrieval")
    _print_chunks("Reranked", trace.ranked, score_kind="both")
    _print_chunks("Used In Prompt", trace.used, score_kind="both")
    print("  ────────────────────────────────────────────────────────────\n")


def _print_chunks(label: str, chunks: list, score_kind: str) -> None:
    print(f"\n  {label}: {len(chunks)}")
    if not chunks:
        return

    for i, chunk in enumerate(chunks, start=1):
        score = f"retrieval={chunk.retrieval_score:.4f}"
        if score_kind == "both" and chunk.rerank_score is not None:
            score += f", rerank={chunk.rerank_score:.4f}"

        source = chunk.title or chunk.path or chunk.id
        print(f"    [{i}] {score}")
        print(f"        source:  {source}")
        if chunk.heading:
            print(f"        heading: {chunk.heading}")
        if chunk.path and chunk.path != source:
            print(f"        path:    {chunk.path}")
        print(f"        text:    {chunk.preview}")
