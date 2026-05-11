# The 9 Chunking Strategies That Made My RAG Pipeline Work
# What I Learned After Achieving a 99/100 Structural Eval Score for My RAG Chunker

Everyone building AI apps eventually hits the same wall.

You've picked a good model. You've set up your vector database. You've followed the tutorials. But when you ask your chatbot a question about your own documentation, it gives you a confident, wrong answer. Or it retrieves completely unrelated content. Or it quotes from a navigation menu.

The problem, almost always, is chunking.

Chunking is the step where you break your documents into small pieces before embedding them. It sounds trivial. It isn't. Get it wrong and no amount of prompt engineering, model upgrades, or retrieval tuning will save you. The AI can only work with what you give it, and if what you give it is garbage, the answers will be too.

I learned this the hard way while building a RAG pipeline from scratch — a real one, pointed at actual developer documentation, expected to give accurate answers to real developer questions. I'm building it in stages: ingestion, chunking, embedding, retrieval, reranking, query rewriting, agentic chat, evals. Each stage gets its own package, numbered in the order data flows through it.

I thought chunking would be the boring part. Get the docs in, split them up, move on. I was wrong. It turned out to be the stage that determined whether everything else worked.

By the end of this article, you'll understand what chunking is, why the obvious approach fails on real documentation, and the 9 patterns I converged on after my naive implementation kept producing bad results. No ML background needed.

---

## First, a quick primer

### What is a "chunk"?

Think of a librarian. When you ask a question, they don't hand you the entire manual. They find the right page or paragraph and hand you that. Chunking works the same way: you break a large document into small, meaningful pieces so the AI can find and return just the relevant bit.

Do it carelessly, and the pieces become useless. That's exactly what I found out.

### What is RAG?

**Retrieval Augmented Generation (RAG)** is a pipeline that takes your documents, splits them into chunks, converts each chunk into a vector (a list of numbers that captures meaning), and at query time finds the chunks closest to your question and hands them to an AI as context. It's how you build a chatbot that answers questions about *your specific* docs without retraining the model.

The critical lesson most tutorials skip: **garbage chunks guarantee garbage retrieval.** No amount of fancy reranking or a bigger model saves you. The embedding model can only encode what you give it.

---

## Where I started, and how it broke

My first version was two lines. Install LangChain, call `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`, done. That's what every tutorial does.

I pointed it at the BudPay developer documentation and ran a quick manual check on the chunks. What I found was not great.

Code blocks were getting split mid-function. I'd see a chunk end with `"amount": "50000",` and the next one start with `"bank_code": "058"`. Two halves of the same curl example, now useless on their own. Tables were splitting between the header row and the data rows, so the AI would retrieve a page of bank codes with no column names — just raw numbers with no context. Markdown links were breaking mid-text: one chunk ending with `[BudPay` and the next starting with `](https://developer.budpay.com)`. And every scraped page was contributing its nav menu and footer links as if they were real documentation.

The bot's answers reflected all of it. Confident-sounding responses, frequently wrong.

This is what naive chunking does on real documentation:

- Code blocks get split mid-function.
- Tables get split between header and data rows.
- Markdown links break at chunk boundaries.
- Navigation menus get indexed as actual content.
- Footer link clouds attach to the last chunk of every page.
- Section headings get separated from the content they describe.

None of it is the AI's fault. It's a pre-processing problem, and it's solvable with plain logic.

So I started fixing things, one bug at a time.

---

## Pattern 1: Split by markdown headers first

**The problem:** The splitter had no awareness of document structure.

When you split purely by character count, the splitter doesn't know or care about section boundaries. It counts to 1,000 characters and cuts, regardless of whether it's in the middle of a heading, a paragraph, or a sentence. What you end up with are chunks that mix content from completely different sections, making each one harder for the AI to interpret accurately.

I'd get chunks like:

```
chunk 2: "ation header.\n\n# Webhooks\n\nConfigure your endpoi"
```

That's the tail end of the Authentication section fused with the start of the Webhooks section. The AI had no idea what that chunk was about, and neither would you if someone handed it to you out of context.

**The fix:** Split by headers first, character count second.

Documentation has structure. Headers (`#`, `##`, `###`) are explicit section boundaries, put there by the author to separate one topic from the next. If I respect those boundaries and split along them first, each chunk maps to one coherent section. Then I handle sections that are still too big separately.

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]

header_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=HEADERS,
    strip_headers=False,   # keep the header inside the chunk
)
header_chunks = header_splitter.split_text(body)
```

The `strip_headers=False` part is critical. I want the header text to stay inside the chunk. That way, when the chunk gets embedded, the vector captures the section name alongside the content. A chunk that starts with `## Authentication` embeds very differently from one that starts mid-sentence with no context.

After this change, the Authentication section became its own chunk and the Webhooks section became its own chunk. Clean, labelled, retrievable.

---

## Pattern 2: Recursive fallback for oversize sections

**The problem:** Some sections are just too big to embed well.

Header splitting solved the mixed-content problem, but it created a new one. Sections like `## Transfer API` or `## Webhook Events` in the BudPay docs run several thousand characters. A single chunk that size is too much for an embedding model to handle well. The model tries to compress everything into one vector, and the result represents nothing with precision. When you query "how do I initiate a bank transfer?", a bloated multi-topic chunk might technically contain the answer but rank poorly because its vector is diluted by everything else in it.

**The fix:** Apply a recursive character splitter inside each header section.

```python
prose_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=200,
)
```

The approach is header-first, recursive-second. A large `## Transfer API` section gets broken into `(part 1/3)`, `(part 2/3)`, `(part 3/3)` at natural paragraph boundaries, never mid-sentence. Each part stays within its parent section, so the context is still scoped correctly.

The 200-character overlap is intentional. It means the tail of one chunk is repeated at the head of the next. This sounds wasteful but it protects against losing a critical sentence that sits right on a boundary. If a key piece of information lands in the overlap zone, both adjacent chunks carry it.

The result is chunks that are small enough to embed precisely and large enough to carry meaningful context.

---

## Pattern 3: Code blocks are atomic

**The problem:** A split code block is not a code block. It's two broken fragments.

This one frustrated me the most before I fixed it. A curl example demonstrating a bank transfer request would split right in the middle of the JSON body. Chunk A would have the request headers and the first few fields. Chunk B would have the remaining fields and the closing syntax. Neither half made any sense on its own.

When a user asked "how do I initiate a transfer?", the retriever would sometimes pull chunk A, sometimes chunk B, sometimes both. The AI would try to construct an answer from an incomplete example and produce something that looked plausible but didn't actually work.

Here's what those split chunks looked like:

```
chunk A: "...Initiate a transfer:\n\n```bash\ncurl -X POST https://api.budpay.com/api/v2/bank_transfer \\\n  -H \"Authorization: Bearer YOUR_SECRET_KEY\" \\\n  -d '{\n    \"currency\": \"NGN\",\n    \"amount\": \"50000\","
chunk B: "    \"bank_code\": \"058\",\n    \"account_number\": \"0123456789\"\n  }'\n```"
```

**The fix:** Detect code fences and treat everything between them as an indivisible unit.

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

When the chunker encounters a fenced code block, it marks it as atomic. Atomic segments get appended whole to the current chunk, even if doing so pushes the chunk over the size limit.

Yes, that occasionally produces an oversized chunk. I made my peace with that trade-off early on. An oversized chunk with a complete, runnable example is useful to the AI. A correctly-sized chunk with half a JSON body is not. You're always better off with slightly too much coherent content than a precisely-sized fragment of something broken.

---

## Pattern 4: Tables are atomic, and always keep their header

**The problem:** Table rows without column headers are just numbers.

I was chunking a 60-row reference table of Nigerian bank codes. The splitter didn't understand table structure, so it treated the table like any other text: count to 1,000 characters, cut. The first 20 rows landed in chunk 1, complete with the header. The next 20 rows went into chunk 2, with no header at all.

Chunk 2 looked like this:

```
| Zenith Bank    | 057  | NGN      |
| First Bank     | 011  | NGN      |
...
```

Now a user asks "what's the bank code for Zenith Bank?" The retriever pulls chunk 2. The AI sees three columns of data but has no idea what they represent. Is "057" a bank code, an area code, a transaction type? It had to guess. Sometimes it guessed right. Often it didn't.

The deeper issue is that column headers give every row its meaning. Without them, tabular data is ambiguous at best and misleading at worst.

**The fix:** Split tables by actual character size first, with row count as a secondary cap, and prepend the header row to every chunk.

The first version of this used a fixed row count — 20 rows per chunk regardless of how wide those rows were. That kept the header on every chunk, which was the main win. But wide rows, like a table with long descriptions or multiple long fields, could still produce oversized chunks that bloated the vector or blew token budgets downstream.

The updated implementation measures the actual size of each accumulated row batch against the configured `chunk_size`. Row count is still used as a safety cap, but the primary split trigger is character length:

```python
def chunk_table(table: str, chunk_size: int, rows_per_chunk: int = 20) -> list[str]:
    header, separator, data = _parse_rows(table)
    prefix = f"{header}\n{separator}\n"
    chunks, batch, batch_len = [], [], len(prefix)
    for row in data:
        row_len = len(row) + 1  # +1 for newline
        if batch and (batch_len + row_len > chunk_size or len(batch) >= rows_per_chunk):
            chunks.append(prefix + "\n".join(batch))
            batch, batch_len = [], len(prefix)
        batch.append(row)
        batch_len += row_len
    if batch:
        chunks.append(prefix + "\n".join(batch))
    return chunks
```

The header prefix is included in the size accounting, so every chunk respects the limit from the first row. Every chunk still starts with `| Bank Name | Code | Currency |`. The AI knows exactly what it's looking at and answers cleanly. Now it also doesn't silently exceed the size budget when rows happen to be wide.

---

## Pattern 5: Repair links split across chunks

**The problem:** Markdown links are invisible to character-based splitters.

A markdown link looks like `[link text](https://url)`. To the recursive splitter, it's just a string of characters. If the split boundary falls in the middle of one, you get two broken fragments: one chunk ending with `[BudPay` and the next starting with `](https://developer.budpay.com)`.

This is subtle and easy to miss until you start manually inspecting chunks. Neither fragment is a valid link. When the AI retrieves either of them, it encounters broken markup that it can't parse into a real URL. Any answer that tries to reference that link will either omit it or construct something wrong.

I spotted this during a manual review pass. It was showing up on multiple pages, quietly poisoning references throughout the documentation.

**The fix:** A post-processing pass that detects and stitches split links back together.

```python
def repair_split_links(chunks: list[str]) -> list[str]:
    open_link  = re.compile(r"\[[^\]]*$")
    close_link = re.compile(r"^[^\[]*\]\(")
    repaired, i = [], 0
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

The logic is straightforward: look for an open bracket near the end of a chunk (`[` with no matching `]`). If the next chunk starts with the closing half (`](url)`), merge the two. The resulting chunk is occasionally a little oversized. That's a small price for intact, working links.

---

## Pattern 6: Drop navigation chunks before embedding

**The problem:** Web scrapers don't know the difference between navigation and content.

When you scrape a documentation website, you don't just get the article text. You get everything the browser renders — the top nav bar, the sidebar links, the breadcrumb trail, the "Skip to main content" link. The scraper captures all of it and hands it to you as text.

When I inspected my raw chunks, I kept finding things like this:

```
[Skip to main content](#main)
[Home](/)
[Docs](/docs)
[API Reference](/api)
[Pricing](/pricing)
```

That chunk got embedded and stored in the vector database just like a real documentation chunk. When a user asked a question, the retriever would sometimes pull it as a match. The AI would receive a list of navigation links as its "context" and try to construct an answer from it. The results were confusing at best and confidently wrong at worst.

**The fix:** Detect and drop navigation chunks before they reach the embedding model.

```python
def is_nav_chunk(text: str) -> bool:
    stripped = text.strip()
    if _SKIP_PATTERN.search(stripped):    # "Skip to main content"
        return True
    lines = [l.strip() for l in stripped.splitlines() if l.strip()]
    if lines and all(_SINGLE_LINK.match(l) for l in lines):
        return True
    return False
```

The rule is simple: if every line in a chunk is a single markdown link and nothing else, it's navigation. Drop it. This filter runs before anything touches the embedding model, so nav content never makes it into the vector database in the first place.

---

## Pattern 7: Strip trailing navigation from the last chunk

**The problem:** Footer navigation doesn't live in its own chunk. It lives at the bottom of a real one.

After pattern 6, I thought I had the nav problem solved. Then I noticed something else. The very last chunk of almost every scraped page looked like this:

```
Use the Authorization header with your secret key for every request.

[← Previous: Getting Started](/getting-started) [Next: Webhooks →](/webhooks) [Back to Top](#top)
```

Real documentation at the top, footer nav glued to the bottom. The nav filter from pattern 6 wouldn't catch it because the chunk also contains legitimate content. Dropping the whole chunk would lose the documentation. Keeping it as-is would dilute the embedding with navigation noise.

The challenge is surgical removal: keep the prose, strip the footer.

**The fix:** Walk backwards through the last chunk's lines, removing any line where markdown links make up more than 60% of the characters.

```python
def strip_trailing_nav(chunks: list[dict]) -> list[dict]:
    last = chunks[-1]["text"]
    lines = last.splitlines()
    while lines and is_link_heavy(lines[-1]):
        lines.pop()
```

The 60% threshold is the key insight here. Prose sentences, even ones that contain a link, are mostly words. A line like "See the authentication guide for more details" has one short link and plenty of surrounding text. A footer nav line like `[← Previous: Getting Started](/getting-started) [Next: Webhooks →](/webhooks)` is almost entirely link syntax. The threshold distinguishes between the two cleanly, without ever touching a line of real content.

---

## Pattern 8: Embed text is not the same as display text

**The problem:** The text inside a chunk doesn't always describe what the chunk is about.

This was the discovery that surprised me the most, and it was hiding in plain sight.

I had a chunk that contained: `"Use a Bearer token in the Authorization header for every request."` A user asks "how do I authenticate to the BudPay API?" The retriever looks for chunks whose vectors are semantically close to that question. But this chunk contains no form of the word "authenticate." It contains "Authorization," "Bearer," and "header" — all accurate, all relevant, but semantically distant from the word "authenticate."

The retriever kept missing this chunk. Consistently. And the AI kept giving vague or wrong answers about authentication as a result.

The problem is that I was embedding the raw chunk text, which is fine for retrieval when queries use the same vocabulary as the documentation. But users don't always do that. They ask in their own words, and their words often don't match the specific phrasing of the documentation.

**The fix:** Give each chunk two versions of its text. A display text for the AI to use when answering. An embed text for building the vector, enriched with surrounding context.

```python
def _add_embed_text(chunks: list[dict]) -> None:
    for chunk in chunks:
        meta = chunk["metadata"]
        parts = [meta.get("title"), " > ".join(meta.get("heading", {}).values()), meta.get("description")]
        parts = [p for p in parts if p]
        chunk["embed_text"] = ("\n".join(parts) + "\n\n" + chunk["text"]) if parts else chunk["text"]
```

The embed text prepends the page title, heading path, and page description from the chunk's metadata. So instead of embedding just the sentence, I embed this:

```
API Basics
Authentication > Overview
Authentication and access control for the BudPay API

Use a Bearer token in the Authorization header for every request.
```

The vector now encodes the page (`API Basics`), the section location (`Authentication > Overview`), and the topic summary, not just the sentence itself. The embedding becomes a much more complete representation of what this chunk is actually about.

After this change, queries like "how do I authenticate?" and "what's the auth flow?" started hitting the right chunk reliably, even when the exact word "authenticate" appeared nowhere in the prose. Of everything I changed, this moved retrieval quality the most.

---

## Pattern 9: Annotate chunks with structural metadata

**The problem:** A retrieved chunk with no provenance is hard to trust, cite, or debug.

This was the last pattern I added, and I almost skipped it because it felt like overhead. Metadata doesn't directly improve retrieval the way the other patterns do. It doesn't fix a broken chunk or improve a vector. It's bookkeeping.

But I kept running into situations where it mattered. When I was building the citation layer, I needed to tell users where an answer came from. "Bank Codes" is a useful citation. An unlabelled blob of pipe-separated characters is not. When a retrieval result looked wrong and I needed to debug it, knowing which rows of which table a chunk represented was the difference between a five-minute fix and an hour of head-scratching.

**The fix:** Record structural context on every chunk at creation time — and make that identity stable.

The first version stored column names and row range on table chunks, which was enough for citations and debugging. But there was a fragility problem I didn't anticipate: chunk IDs were positional. A chunk was identified as `0_1` meaning "document 0, chunk 1." If I updated a single page and re-ran the chunker, every chunk after the changed page shifted its index. Unchanged chunks got new IDs. The vector store had no way to know which chunks were genuinely new and which had just moved.

I updated the identity model. Every chunk now gets three identity fields:

```python
chunk["content_hash"]  = sha256(chunk["embed_text"])   # normalized content fingerprint
chunk["chunk_id"]      = f"{doc_slug}_{content_hash[:8]}"  # stable, content-based ID
chunk["chunk_index"]   = position                       # positional index, preserved separately
```

The `content_hash` is computed from the embed text after normalisation, so minor whitespace differences don't create false mismatches. The `chunk_id` is built from the document slug and the hash, making it stable across re-indexing runs as long as the content hasn't changed. The old positional index is preserved as `chunk_index` for cases where order matters, like reconstructing a table from its parts.

For table chunks specifically, I also added a shared `table_id` across all chunks that came from the same source table:

```python
chunk["metadata"]["table_id"]  = f"{doc_slug}_table_{table_index}"
chunk["metadata"]["columns"]   = parse_headers(chunk["text"])
chunk["metadata"]["row_start"] = 21
chunk["metadata"]["row_end"]   = 40
```

The full metadata object for a table chunk now looks like this:

```python
{
    "text": "| Bank Name | Code | Currency |\n|...| Zenith Bank | 057 | NGN |...",
    "content_hash": "a3f8c21d",
    "chunk_id":     "banks_a3f8c21d",
    "chunk_index":  4,
    "metadata": {
        "table_id":  "banks_table_2",
        "columns":   ["Bank Name", "Code", "Currency"],
        "row_start": 21,
        "row_end":   40,
        "title":     "Bank Codes",
        "heading":   {"h2": "Reference Tables"},
        "path":      "https://developer.budpay.com/banks"
    }
}
```

This pays off in four places now. The reranker uses column names to score table relevance. The citation layer shows "Bank Codes, rows 21 to 40." Debugging a bad retrieval result is fast because I can trace the exact document, section, and row range. And re-indexing is safe: unchanged chunks keep their IDs, so only genuinely new or modified chunks get re-embedded. On large documentation sets, that last point makes incremental updates significantly cheaper.

The principle generalises to all chunk types: every chunk should carry enough information that you could reconstruct exactly where it came from without looking at the source document. Future you, debugging a bad retrieval result at 11pm, will be grateful.

---

## Putting it all together

Here is how all nine patterns compose into a single function:

```python
def chunk_file(filepath: str, config: ChunkerConfig | None = None) -> list[dict]:
    cfg = config or ChunkerConfig()
    raw = re.sub(r"!\[\]\([^)]+\)", "", open(filepath).read())
    frontmatter, body = parse_frontmatter(raw)

    header_chunks = header_splitter.split_text(body)          # 1. headers first

    chunks = []
    for doc in header_chunks:
        sub_chunks = _code_aware_split(doc.page_content, cfg.chunk_size, cfg.chunk_overlap)
        # 2. recursive fallback, 3. atomic code, 4. atomic tables, 5. link repair
        for text in sub_chunks:
            text = strip_horizontal_rules(text)
            if not text.strip() or len(text.strip()) < cfg.min_chunk_length:
                continue
            if is_nav_chunk(text):                             # 6. nav filter
                continue
            chunks.append({"text": text, "metadata": {...}})

    chunks = strip_trailing_nav(chunks)                        # 7. trailing nav
    _annotate_table_chunks(chunks)                             # 9. metadata
    _add_embed_text(chunks)                                    # 8. embed != display
    return chunks
```

Nine patterns, around 150 lines, one function. Each comment maps to a pattern above.

---

## The results

I ran two evals when I was done: one at the full pipeline level, and one scoped to just the chunker.

### End-to-end RAG eval

36 questions over real documentation, judged on retrieval quality and answer correctness:

```
Quality score      97.4/100   Excellent
Retrieval hit      36/36
Top-1 hit          34/36
Mean reciprocal    0.968
Valid citations    36/36
```

Here's what each number actually means:

**Retrieval hit 36/36.** Every single question retrieved at least one correct source chunk. This is the baseline. If the right chunk isn't retrieved at all, the AI has nothing to work with. A clean sweep here means the chunker is giving the retriever coherent material.

**Top-1 hit 34/36.** For 34 out of 36 questions, the correct chunk was ranked first. Not buried at position 3, first. This matters because most pipelines only pass the top 1 or 2 chunks to the AI. If the best chunk isn't near the top, the answer suffers.

**Mean Reciprocal Rank (MRR) of 0.968.** MRR measures how high up the correct chunk appears on average. A score of 1.0 means it's always first. 0.968 means it's first or second almost every time. An MRR below 0.7 usually means something is wrong upstream.

**Valid citations 36/36.** Every answer cited a real, valid chunk. No hallucinated sources. This is a direct result of chunks being coherent and well-labelled.

### Chunker-level audit

A separate audit run directly on the produced chunks, after the pipeline improvements:

```
Quality score:        99.3/100
Code block integrity: 100%
Link integrity:       100%
Size compliance:      99.4%
Nav noise:            0.8%
Duplicate rate:       3.6%  ⚠
```

**Code block integrity 100%.** Not a single code block was split mid-function.

**Link integrity 100%.** Every markdown link survived intact. No broken fragments made it through.

**Size compliance 99.4%.** The size-aware table splitting in pattern 4 directly moved this number. The old fixed-row-count approach was the main source of oversized chunks. Now that table splitting respects `chunk_size` as the primary constraint, nearly every chunk lands within budget. The remaining 0.6% are atomic code blocks that intentionally exceed the limit because breaking them would be worse.

**Nav noise 0.8%.** Less than 1% of chunks are navigation noise. The filter is doing its job.

**Duplicate rate 3.6%, the only warning.** This comes mostly from the intentional 200-character overlap and boilerplate intro paragraphs that appear across multiple pages. A content-hash dedupe pass would close it cleanly. It's on my list, and the stable `content_hash` on every chunk makes that pass straightforward to implement now.

---

## Key takeaways

- **Headers are a free signal.** Use them first, before anything else.
- **Code blocks and tables are atomic.** Never split them internally.
- **Tables need their header on every chunk.** Rows without column names are useless.
- **Repair split links.** A post-process pass takes about ten lines.
- **Nav noise is filterable with regex.** No model needed.
- **Embed text is not display text.** Add context to the vector, not to the prompt.
- **Every chunk should know where it came from.** Metadata compounds over time.
- **Measure everything.** Without an eval, you are guessing.

When I started, I assumed chunking was the part I'd spend the least time on. It turned out to be the part that determined whether everything else worked. The retriever, the reranker, the AI model — they all depend on getting coherent input. Get the chunker right, measure the result, and most other tuning becomes optional.
