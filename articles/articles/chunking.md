# Chunking Strategies for RAG: 9 Patterns That Pushed My Chunker to 99/100

## What I'm building, and why this matters

I'm building an open-source RAG pipeline from scratch — ingestion, chunking,
embedding, retrieval, reranking, query rewriting, agentic chat, evals. The
whole thing. I write each stage as a numbered package
(`rag/stg_02_chunker`, `rag/stg_03_embedder`, ...) so the codebase reads in
the order the data flows.

If you haven't lived inside RAG yet: the short version is that a Retrieval
Augmented Generation pipeline takes a body of documents, splits them into
chunks, embeds each chunk into a vector, and at query time finds the chunks
closest to your question and feeds them to an LLM as context. RAG is what
lets ChatGPT-style assistants answer questions about your specific
documentation, codebase, or knowledge base — without retraining the model.

Most RAG tutorials gloss over the boring stage. They install a library,
call `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`,
embed the output, and call it done. That works on a clean blog post. It
falls apart the moment you point it at real documentation.

Here's why I pay attention to chunking specifically: **garbage chunks
guarantee garbage retrieval, and no amount of fancy reranking,
sophisticated prompts, or a bigger model will save you from that.** The
embedding model can only encode what you give it. If your chunk is half a
code block and a piece of a footer nav, the vector you store is also half
nonsense.

Get chunking right and most other RAG tuning becomes optional. Here are
the nine patterns I converged on.

## What naive chunking breaks

Pointing a fixed-size splitter at a typical docs site, you'll find:

- Code blocks split mid-function, so the embedded chunk has half a curly
  brace and no closing tag.
- Tables split between header and body, so the model retrieves rows with
  no column names.
- Markdown links split across the chunk boundary: `[Bud` ...
  `Pay](https://...)`.
- Navigation menus and "Skip to content" links indexed as if they were
  documentation.
- The footer link cloud appended to the last chunk of every page.
- Headings stripped from the section they describe, so the chunk is
  contextless prose.

Each of these makes retrieval worse. None of it is the LLM's fault. It's a
pre-processing problem, and it's solvable with regex, not a model.

## 1. Split by markdown headers first

Documentation has structure. Headers (`#`, `##`, `###`) almost always mark
section boundaries. If you split by character count first and headers
second, you'll cut sections in half. If you split by headers first,
sections stay intact.

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]

header_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=HEADERS,
    strip_headers=False,
)
header_chunks = header_splitter.split_text(body)
```

`strip_headers=False` is the important part. The header line goes into the
chunk so the embedded vector reflects the section name, not just its body.

**Example.** Take a docs page like:

```markdown
# Authentication

Use a Bearer token in the Authorization header.

# Webhooks

Configure your endpoint in the dashboard.
```

A naive 50-character splitter produces:

```
chunk 1: "# Authentication\n\nUse a Bearer token in the Authoriz"
chunk 2: "ation header.\n\n# Webhooks\n\nConfigure your endpoi"
chunk 3: "nt in the dashboard."
```

Chunk 2 is now half-Auth, half-Webhooks. The embedding has no idea what it's
about. With header-first splitting:

```
chunk 1: "# Authentication\n\nUse a Bearer token in the Authorization header."
chunk 2: "# Webhooks\n\nConfigure your endpoint in the dashboard."
```

Now each chunk is a coherent topic.

## 2. Recursive fallback for oversize sections

Some sections are still too big. A 10,000-character "API Reference" page
won't fit in a single chunk no matter how nicely it's headed. So a
recursive character splitter handles overflow:

```python
prose_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=200,
)
```

Header-first, recursive-second. Sections fit when they fit; long sections
get split at paragraph boundaries inside their section.

**Example.** A 5,000-char `## Transfer API` section gets header-split into
one big chunk first. The recursive splitter then breaks it into
`Transfer API (part 1/3)`, `(part 2/3)`, `(part 3/3)` at paragraph
boundaries — never mid-sentence. The 200-character overlap means each part
shares its tail with the next part's head, so retrieval doesn't lose
context across the boundary.

## 3. Code blocks are atomic

This is where naive chunking starts producing nonsense. A code block of
1,500 characters straddles a 1,000-char boundary, gets split, and you embed
half a function with no syntax context.

The fix: detect code fences and treat them as indivisible units.

```python
def _extract_blocks(text: str) -> list[tuple[str, bool]]:
    segments = []
    for part in re.split(r"(```[\s\S]*?```)", text):
        if part.startswith("```"):
            segments.append((part, True))   # is_atomic
        else:
            segments.extend(segment_tables(part))
    return segments
```

The chunker iterates over these segments. Atomic ones are appended whole,
even if they exceed the chunk size.

**Example.** A long curl example:

````markdown
Initiate a transfer:

```bash
curl -X POST https://api.budpay.com/api/v2/bank_transfer \
  -H "Authorization: Bearer YOUR_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "NGN",
    "amount": "50000",
    "bank_code": "058",
    "account_number": "0123456789",
    "narration": "Vendor payment"
  }'
```
````

A naive splitter would cut between `"amount":` and `"bank_code":`, leaving
half a JSON body in each chunk. With code-aware splitting, the entire
fenced block stays in one chunk. The cost is the occasional oversized
chunk; the benefit is that the LLM sees a complete, runnable example.

## 4. Tables are atomic, but row-aware

Tables raise the same problem as code, with an extra twist: the header row
matters for every other row. A 100-row currency table with header
`| Bank | Code | Currency |` is useless if you embed rows 50-60 without
the header.

Two patterns combine:

**Detection** — a contiguous run of `|...|` lines is a table block.

**Header preservation** — when a table is too big to fit in one chunk,
split it by row count, but **prepend the header to every chunk**.

```python
def chunk_table(table: str, rows_per_chunk: int = 20) -> list[str]:
    header, separator, data = _parse_rows(table)
    prefix = f"{header}\n{separator}\n" if separator else f"{header}\n"
    chunks = []
    for i in range(0, len(data), rows_per_chunk):
        batch = data[i: i + rows_per_chunk]
        chunks.append(prefix + "\n".join(batch))
    return chunks
```

**Example.** Source table with 60 banks:

```markdown
| Bank Name      | Code | Currency |
|----------------|------|----------|
| GTBank         | 058  | NGN      |
| Access Bank    | 044  | NGN      |
... (58 more rows)
```

Without header preservation, chunk 2 starts at row 21:

```markdown
| Zenith Bank    | 057  | NGN      |
| First Bank     | 011  | NGN      |
...
```

A user asks "what's the code for Zenith Bank?", we retrieve chunk 2, and
the LLM has no idea what the columns mean. Code? Phone area code? Postal
code? With header preservation, every chunk looks like:

```markdown
| Bank Name      | Code | Currency |
|----------------|------|----------|
| Zenith Bank    | 057  | NGN      |
| First Bank     | 011  | NGN      |
...
```

The LLM sees `Bank Name → Code → Currency` and answers cleanly.

## 5. Repair links split across chunks

Markdown links don't survive naive splitting. A 1,000-character chunk can
end with `See [Bud` and the next chunk starts with `Pay](https://...) for
details.` Both chunks now contain unparseable markup.

The fix is small: walk the chunks, look for an open `[` near the end of one
chunk and the matching `](` at the start of the next, and merge.

```python
def repair_split_links(chunks: list[str]) -> list[str]:
    open_link  = re.compile(r"\[[^\]]*$")
    close_link = re.compile(r"^[^\[]*\]\(")

    repaired = []
    i = 0
    while i < len(chunks):
        chunk = chunks[i]
        if i + 1 < len(chunks) and (open_link.search(chunk) or close_link.match(chunks[i + 1])):
            repaired.append(chunk + chunks[i + 1])
            i += 2
        else:
            repaired.append(chunk)
            i += 1
    return repaired
```

**Example.** Before repair:

```
chunk 5: "...for the full reference, see [BudPay"
chunk 6: "](https://developer.budpay.com) for the latest API."
```

Both chunks contain garbage markup. After repair:

```
chunk 5: "...for the full reference, see [BudPay](https://developer.budpay.com) for the latest API."
```

Two chunks become one. The merged chunk is occasionally oversized. Better
an oversized chunk than a broken link.

## 6. Drop navigation chunks before embedding

Web-scraped documentation includes navigation menus, "Skip to content"
links, breadcrumbs, and footer link clouds. None of this is content. It's
boilerplate that pollutes embeddings and pulls retrieval scores in the
wrong direction.

A small filter catches the most common patterns:

```python
def is_nav_chunk(text: str) -> bool:
    stripped = text.strip()
    if _SKIP_PATTERN.search(stripped):           # "Skip to main content"
        return True
    if _SINGLE_LINK.match(stripped):             # "[Home](/)"
        return True
    lines = [l.strip() for l in stripped.splitlines() if l.strip()]
    if lines and all(_SINGLE_LINK.match(l) for l in lines):  # all-links chunk
        return True
    return False
```

**Example.** A scraped page yields a chunk like:

```
[Skip to main content](#main)

[Home](/)
[Docs](/docs)
[API Reference](/api)
[Pricing](/pricing)
```

This is pure navigation. There's no content. `is_nav_chunk()` returns
`True` and the chunker drops it before it ever hits the embedding model.

## 7. Strip trailing navigation from the last chunk

The last chunk of a page is special — it usually has the footer's
"Previous / Next / Home" link block glued to the end. Dropping the entire
chunk would lose real content; keeping it as-is dilutes the embedding.

The fix is to walk backwards through the last chunk's lines, peeling off
link-heavy lines until we hit prose:

```python
def strip_trailing_nav(chunks: list[dict]) -> list[dict]:
    last = chunks[-1]["text"]
    lines = last.splitlines()
    while lines and is_link_heavy(lines[-1]):
        lines.pop()
    # ... reassemble or drop the chunk if nothing's left
```

`is_link_heavy` returns True when markdown links cover more than 60% of a
line's characters. A real prose line never hits that threshold; a footer
nav line always does.

**Example.** Last chunk before strip:

```
Use the Authorization header with your secret key for every request.

[← Previous: Getting Started](/getting-started) [Next: Webhooks →](/webhooks) [Back to Top](#top)
```

After strip:

```
Use the Authorization header with your secret key for every request.
```

The footer nav is gone. The actual content is preserved.

## 8. Embed text ≠ display text

This is the single most underrated chunking pattern, and most tutorials
skip it entirely.

The text you show the LLM at answer time and the text you embed don't have
to be the same. The display text is the chunk's prose. The embed text
should include the surrounding context — page title, heading path,
description — so the embedding vector reflects what the chunk is *about*,
not just what words it contains.

```python
def _add_embed_text(chunks: list[dict]) -> None:
    for chunk in chunks:
        meta = chunk["metadata"]
        parts = []

        if meta.get("title"):
            parts.append(meta["title"])

        heading = meta.get("heading", {})
        if heading:
            parts.append(" > ".join(heading.values()))

        if meta.get("description"):
            parts.append(meta["description"])

        embed_text = ("\n".join(parts) + "\n\n" + chunk["text"]) if parts else chunk["text"]
        chunk["embed_text"] = embed_text
```

**Example.** Display text (what the LLM sees in the prompt at answer time):

```
Use a Bearer token in the Authorization header for every request.
```

Embed text (what we hash into the vector):

```
API Basics
Authentication > Overview
Authentication and access control for the BudPay API

Use a Bearer token in the Authorization header for every request.
```

The vector now encodes the page (`API Basics`), the section path
(`Authentication > Overview`), and the topic — not just the sentence.

This shifted retrieval quality more than any other change I made. Queries
like "how do I authenticate?" and "what's the auth flow?" now pull the
right chunk reliably, even when the chunk's prose doesn't contain the
exact word "authenticate".

## 9. Annotate chunks with structural metadata

A retrieved chunk is more than its text. Its position in the source
document matters too. For tables specifically, the chunker records which
rows the chunk covers and what the columns are:

```python
def _annotate_table_chunks(chunks: list[dict]) -> None:
    for chunk in chunks:
        if not _is_table_chunk(chunk):
            continue
        chunk["metadata"]["columns"]   = parse_headers(chunk["text"])
        chunk["metadata"]["row_start"] = ...
        chunk["metadata"]["row_end"]   = ...
```

**Example.** A table chunk for rows 21-40 of the bank list now carries:

```python
{
    "text": "| Bank Name | Code | Currency |\n|-----------|------|----------|\n| Zenith Bank | 057 | NGN |\n...",
    "metadata": {
        "columns":   ["Bank Name", "Code", "Currency"],
        "row_start": 21,
        "row_end":   40,
        "title":     "Bank Codes",
        "heading":   {"h2": "Reference Tables"},
        "path":      "https://developer.budpay.com/banks",
        ...
    }
}
```

This metadata isn't used at retrieval time directly, but it pays off in two
places:

- **Reranking**: a cross-encoder can use the column names to score table
  relevance more accurately.
- **Display / citation**: the UI can show "Bank Codes — rows 21–40 of 60"
  instead of an opaque text blob, and citations can point at the precise
  row range.

The pattern generalizes: every chunk should know enough about its source
that you could reconstruct where it came from.

## Putting it together

The full chunking pipeline, end to end:

```python
def chunk_file(filepath: str, config: ChunkerConfig | None = None) -> list[dict]:
    cfg = config or ChunkerConfig()
    raw = open(filepath).read()
    raw = re.sub(r"!\[\]\([^)]+\)", "", raw)             # strip empty images
    frontmatter, body = parse_frontmatter(raw)

    header_chunks = header_splitter.split_text(body)     # 1. headers first

    chunks = []
    for i, doc in enumerate(header_chunks):
        sub_chunks = _code_aware_split(doc.page_content, cfg.chunk_size, cfg.chunk_overlap)
        # 2. recursive fallback inside _code_aware_split
        # 3. atomic code, 4. atomic tables, 5. link repair all happen there
        for j, text in enumerate(sub_chunks):
            text = strip_horizontal_rules(text)
            if not text.strip() or len(text.strip()) < cfg.min_chunk_length:
                continue
            if is_nav_chunk(text):                       # 6. nav filter
                continue
            chunks.append({"text": text, "metadata": {...}})

    chunks = strip_trailing_nav(chunks)                  # 7. trailing nav strip
    _annotate_table_chunks(chunks)                       # 9. structural metadata
    _add_embed_text(chunks)                              # 8. embed != display
    return chunks
```

Nine patterns, around 150 lines of pre-processing, in a function you can
read in one sitting.

## Did it work? The numbers

Two evals confirm the chunker is doing its job.

**End-to-end RAG eval** — golden dataset of 36 questions over OpenCode's
documentation, judged for retrieval quality and answer correctness:

```
uv run python -m rag.stg_05_chat.eval \
    --collection opencode_rag_chunks \
    --golden files/eval/opencode_rag_golden.jsonl \
    --rewrite-context "OpenCode documentation" \
    --judge

────────────────────────────────────────────────────────────────────────
  Quality score      97.4/100   Excellent
  Retrieval hit      36/36
  Top-1 hit          34/36
  Mean reciprocal    0.968
  Valid citations    36/36
════════════════════════════════════════════════════════════════════════
```

Every question retrieved at least one expected source. 34 out of 36 had
the right chunk in the top spot. MRR of 0.968 says the right chunk is
almost always either first or second. All 36 answers cited valid chunks.

**Chunker-level audit** (separate scorer, run by Codex on the same
corpus):

```
638 chunks
Quality score:        99.2/100   Excellent
Size compliance:      98.6%
Nav noise:            0.8%
Code block integrity: 100%
Link integrity:       100%
Heading coverage:     99.7%
Embed text coverage:  100%
Duplicate rate:       3.6%       warning
```

100% on code blocks, 100% on links, 100% on embed text coverage. Heading
coverage at 99.7% means almost every chunk knows what section it came
from. Nav noise under 1% means the filter is doing its job.

## What I'd still improve

Two things are worth flagging:

**1. The 3.6% duplicate rate.** This is the only warning in the audit,
and it deserves a look. The most likely sources are:

- The 200-character `chunk_overlap` on recursive splits, which by design
  introduces overlap text. Some of that overlap may be hashing identically
  across pages.
- Boilerplate sections (frontmatter excerpts, common intro paragraphs)
  appearing on multiple pages.
- The same code block embedded in multiple guides.

I'd add a content-hash dedupe pass after embed-text generation: if two
chunks have identical or near-identical embed_text, keep the one whose
heading path is more specific. Cheap to implement, cheap to run.

**2. The 1.4% size non-compliance.** Almost certainly the atomic
code/table chunks that exceeded the cap. That's intentional — better an
oversized chunk than a broken one — but it's worth verifying with a quick
distribution histogram. If any chunk is wildly over (say, 10x the cap),
it'll blow up token budgets at retrieval time.

**3. Heading coverage at 99.7%.** Two chunks per thousand lack heading
metadata. These are probably preamble paragraphs before the first H1, or
files where the splitter treated the entire document as a single
unheaded block. Worth a one-liner that injects the page title as an
implicit `h1` when no header was matched.

**4. No unit tests on the chunker.** The audit gives us a coarse quality
signal, but I'd want a small fixture-based test suite that locks in the
behaviour of `_code_aware_split`, `chunk_table`, `repair_split_links`, and
`is_nav_chunk` against synthetic inputs. Today, refactoring any one of
those means re-running the audit on real data and hoping nothing
regressed silently.

## What this isn't

This isn't semantic chunking. There's no clustering of similar paragraphs,
no GPT call to reflow content, no learned splitter. Those approaches help
in specific cases but they're slow, expensive, and frequently overkill.

The patterns above are deterministic. They run in milliseconds, produce
identical output across runs, and are debuggable with regex and `print`.
For documentation — structured, header-driven, code-and-table-heavy —
they cover the bulk of what fancier methods would buy you.

If your corpus is unstructured (legal documents, transcripts, novels), you
need different patterns. But for docs, this is the floor, not the ceiling.

## Takeaways

- Headers are a free signal. Use them first.
- Code blocks and tables are atomic. Never split them internally.
- Tables need their headers prepended to every chunk.
- Markdown links survive splitting only if you repair them.
- Most navigation noise can be filtered with regex, no model needed.
- Embedding text and display text are separate concerns. Augment one
  without changing the other.
- Every chunk should carry enough metadata to know where it came from.
- Measure. Without an eval, you're guessing.

The reason RAG quality varies so much across systems isn't usually the
embedding model or the LLM. It's whether the chunks are coherent in the
first place. Get the chunker right, measure the result, and most other
tuning becomes optional.
