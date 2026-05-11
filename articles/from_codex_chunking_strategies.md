# From Codex: Chunking Strategies Employed in This RAG Pipeline

Chunking is one of the most important parts of this RAG system. It decides what
the embedding model sees, what the retriever can find, what the reranker can
compare, and what evidence the final answer can cite.

The strategy in this codebase is not just "split every N characters." It is a
layered strategy designed for documentation-heavy corpora: API docs, markdown
pages, tables, code examples, configuration snippets, legal pages, and scraped
website content.

The chunking pipeline lives in:

```text
rag/stg_02_chunker/
```

The main implementation is:

```text
rag/stg_02_chunker/chunker.py
```

## 1. Document-Native Chunking

The first strategy is to respect the shape of the document before thinking
about size.

The pipeline starts from markdown files produced by ingestion. Those markdown
files contain frontmatter-like metadata and body content. The chunker parses
that metadata first, then chunks the body.

This matters because the source page already knows things the raw text does not:

- page title
- source path or URL
- description
- original document type
- crawl source

That metadata is carried into every chunk. The result is that a chunk is not
just a piece of text; it is a piece of text with source identity.

This is essential for:

- citation rendering
- debug traces
- eval source matching
- re-indexing decisions
- source-specific filtering later

## 2. Heading-First Semantic Splitting

The second strategy is heading-first splitting.

Instead of immediately splitting by character length, the chunker first splits
markdown by heading levels:

```text
#
##
###
```

This is a good fit for documentation because headings usually mark semantic
boundaries. A section called `Payout Fees`, `Authentication`, `Webhooks`, or
`Server to Server Cards` is already a retrieval unit.

For example, this:

```md
### Payout Fees

Calculate the transaction fee for a bank transfer before initiating the payout.
```

should stay tied to `Payout Fees`. If the body is embedded without the heading,
a query like "how do I calculate payout fees" becomes harder to match.

The heading metadata is preserved and later added to `embed_text`, so the
embedding model sees both the content and the semantic label around the content.

## 3. Recursive Prose Splitting

Once a heading section is isolated, the chunker checks whether it fits within
the configured size target.

For prose, it uses a recursive text splitter with:

```python
chunk_size = 2000
chunk_overlap = 200
```

The goal is to split large prose sections at natural boundaries before falling
back to smaller boundaries. This is useful for long explanation pages where a
single heading section may contain multiple ideas.

The overlap gives adjacent chunks some shared context. That helps when a concept
starts at the end of one chunk and continues into the next.

This strategy is best for normal paragraphs, explanations, and prose-heavy docs.

## 4. Atomic Block Detection

The fourth strategy is to detect blocks that should not be split casually.

The chunker treats these as atomic blocks:

- fenced code blocks
- markdown tables

This is important because ordinary recursive splitting can damage structured
content.

For example, a broken JSON response is worse than a large JSON response. A
broken cURL request may omit the header or body that makes the example useful. A
table row without its header becomes ambiguous.

So the chunker first extracts code blocks and table blocks, then applies
special handling to them.

## 5. Code-Aware Splitting

Code blocks are preserved as whole units.

This means fenced examples like:

```md
```json
{
  "success": true,
  "message": "Transfer Fee Fetched"
}
```
```

are not split in the middle.

That is the right default for API documentation. Code examples often need their
surrounding structure to be useful: headers, endpoint, request body, response
fields, status code, and closing braces.

The tradeoff is that some code/config blocks can exceed the normal chunk size.
That is currently accepted to preserve correctness. The remaining oversized
chunks after our latest eval are mostly large code/config/legal blocks, not
tables.

Future improvement: split large JSON/YAML/config blocks by logical boundaries
while still preserving fenced-code validity.

## 6. Table-Aware Splitting

Tables get their own strategy because they are common in API documentation:

- endpoint parameters
- response fields
- bank lists
- model lists
- status codes
- configuration options

The rule is simple:

> Every table chunk must carry the table header.

A table row like this:

```md
| account_number | Dedicated NUBAN account number |
```

is much less useful without:

```md
| Field | Description |
| --- | --- |
```

So when a large table is split, the header and separator are repeated on every
chunk.

The table splitter is now also size-aware. It accumulates rows until adding the
next row would exceed `chunk_size`, while keeping `rows_per_chunk` as a
secondary cap.

This gives us both:

- semantic completeness, because each chunk has the table header
- size discipline, because long rows no longer create huge chunks

That change improved size compliance from `98.6%` to `99.4%` on the current
OpenCode corpus.

## 7. Metadata-Enriched Chunks

Each chunk carries metadata:

```json
{
  "source": "...",
  "path": "...",
  "title": "...",
  "description": "...",
  "original_type": "...",
  "heading": "...",
  "chunk_id": "...",
  "id": "..."
}
```

Table chunks also get:

```json
{
  "columns": ["Field", "Description"],
  "row_start": 1,
  "row_end": 20
}
```

This makes chunks useful beyond embedding. The metadata supports:

- source display
- chunk-level citations
- `/debug` trace output
- eval matching through `expected_sources`
- future metadata filtering
- future stale-vector cleanup

This is a key part of the design: the chunk is both an embedding unit and an
evidence object.

## 8. Separate `text` and `embed_text`

The chunker stores two versions of content:

```text
text
embed_text
```

`text` is the clean chunk body used for display and final answer context.

`embed_text` is enriched for retrieval. It includes:

- title
- heading path
- description
- chunk body

This is one of the most important strategies in the system.

The embedding model benefits from extra context, but the user does not need to
see that extra context repeated everywhere. Separating `text` from `embed_text`
keeps retrieval strong and output clean.

## 9. Navigation and Noise Filtering

Scraped websites often contain noise:

- skip links
- footer links
- next/previous navigation
- copyright text
- repeated legal boilerplate
- link-heavy blocks

The chunker includes filters to remove some of that noise:

- navigation-only chunks
- single-link chunks
- link-heavy trailing footer lines
- trailing horizontal rules
- split markdown links

This keeps the vector database cleaner.

The current implementation is conservative. It removes obvious noise without
trying to over-clean the document. That is a reasonable default because
aggressive filters can accidentally delete real documentation content.

The remaining warning in the chunk eval is duplicate text, mostly from repeated
privacy/legal sections and footer-like content. That is the next place to
improve.

## 10. Stable Structural Evaluation

The chunker also has a deterministic eval suite.

It checks:

- size compliance
- navigation noise
- code block integrity
- markdown link integrity
- heading coverage
- embed text coverage
- duplicate rate

After the latest table splitting fix, the current OpenCode corpus reports:

```text
38 files
641 chunks

Size mean/median:      605 / 450 chars
Size min/max:          100 / 3526 chars
Size compliance:       99.4%
Nav noise:             0.8%
Code block integrity:  100.0%
Link integrity:        100.0%
Heading coverage:      99.7%
Embed text coverage:   100.0%
Duplicate rate:        3.6%

Quality score:         99.3 / 100 Excellent
```

This eval is useful because chunking bugs are easy to miss by inspection. The
eval catches structural failures before they become retrieval failures.

## How the Strategies Work Together

The chunking system is layered:

```text
document metadata
→ heading-aware sections
→ code/table block detection
→ prose/table-specific splitting
→ cleanup filters
→ metadata enrichment
→ embed_text construction
→ structural eval
```

Each layer solves a different problem.

Heading splitting protects meaning.

Code preservation protects syntax.

Table splitting protects row/header relationships.

Metadata protects source traceability.

`embed_text` improves retrieval.

Cleanup filters reduce noise.

Eval makes the quality visible.

That is the overall strategy: preserve structure first, enforce size second,
enrich for retrieval third, and verify with evals.

## What This Strategy Is Best For

This approach is especially strong for:

- API documentation
- developer guides
- markdown docs
- structured tables
- code-heavy pages
- product documentation
- docs with meaningful headings

It is less ideal, without further work, for:

- very large source code files
- PDFs with poor heading structure
- legal pages with repeated boilerplate
- pages with huge embedded SVG/base64 assets
- deeply nested tables

## Remaining Improvements

The next improvements are clear.

1. **Code/config-aware splitting**
   Large JSON, YAML, and config examples should be split by logical boundaries,
   not left oversized forever.

2. **Normalized deduplication**
   Repeated legal/privacy sections and footer fragments should be deduped before
   embedding.

3. **Better footer cleanup**
   Footer cleanup should run per chunk and include known footer phrases.

4. **Content-hash IDs**
   Chunk IDs currently depend on file path and position. Content-aware IDs would
   make re-indexing and stale vector cleanup safer.

5. **Token-aware sizing**
   Character count is a useful proxy, but token-aware sizing would better match
   embedding and LLM context limits.

## Summary

The chunking strategy in this RAG pipeline is production-shaped because it treats
chunks as structured evidence, not arbitrary text slices.

The core philosophy is:

> Preserve meaning and structure first. Then control size. Then enrich for
> retrieval. Then evaluate the result.

That is why the pipeline performs well on documentation corpora. It does not
just create chunks that fit into an embedding model. It creates chunks that can
be retrieved, reranked, cited, debugged, and evaluated.
