# Why Markdown Is the Best Ingestion Format for RAG

When I started my RAG pipeline, the first decision I had to make wasn't
which embedding model to use, or what vector database to pick, or how big
my chunks should be. It was something more boring and more important:

**What format do I store the source data in?**

The answer turned out to matter more than every model decision I made
later. I picked markdown. This article explains why, how I convert four
very different source types — web pages, REST APIs, local files (PDF/CSV/
DOCX), and MCP servers — into markdown, and how that single decision
quietly carries the rest of the pipeline.

## What a RAG ingester actually does

If you're new to RAG: a Retrieval-Augmented Generation pipeline takes a
corpus of documents, splits them into chunks, embeds each chunk into a
vector, and at query time retrieves the chunks closest to your question
and feeds them to an LLM as context. The ingester is the very first stage
— it pulls raw content from sources and writes it to disk in whatever
format the rest of the pipeline can consume.

Most RAG tutorials skip past this stage. They start the story at "I have
some text files" and never explain what happened before. In practice,
ingestion is where you make the choice that everything else has to
respect: **what is the canonical format your pipeline thinks in?**

## Candidate formats I considered

I had a few real options. Here's the honest comparison.

**Plain text.** Simple. No structure. The chunker would have nothing to
work with — no headings to split on, no code fences to keep atomic, no
tables to detect. Cheap to produce, expensive to use.

**HTML.** Preserves structure but is verbose, full of attributes nobody
needs, and a nightmare to chunk. I'd have to strip styles, scripts, ads,
and navigation. Even after stripping, retrieval-time prompts would be 30%
markup tags. The LLM tokenizes `<div class="...">` instead of content.

**JSON.** Natural for API responses. But documentation isn't naturally
structured as JSON — converting prose to JSON and back loses the prose's
shape. And the chunker would need a JSON-aware splitter, which doesn't
generalize across sources.

**Custom binary format.** Worst case. Every tool in the pipeline would
need a parser. No off-the-shelf splitter, viewer, or diff tool would work.

**Markdown.** Lightweight. Text-first. Headings, lists, code fences,
tables, and links are all expressible. Every LLM I'd plausibly use
understands markdown natively. Splitters, regex, `cat`, and a code editor
all just work.

The decision wasn't close. Markdown won on every dimension that mattered.

## How each source becomes markdown

The catch with markdown is that none of my sources start as markdown.
Web pages are HTML, APIs return JSON, PDFs are layout-positioned text,
MCP returns native protocol messages. Each one needs a converter.

Here's how each of the four ingesters in `rag/stg_01_ingestors/` does it.

### URL — crawl4ai's markdown extractor

For web pages I use [crawl4ai](https://github.com/unclecode/crawl4ai),
which runs a headless browser and emits markdown directly:

```python
async with AsyncWebCrawler(config=_BROWSER_CONFIG) as crawler:
    result = await crawler.arun(url=url, config=config)
    markdown = result.markdown   # already markdown, headings preserved
```

crawl4ai handles the HTML→markdown conversion internally. It strips
`<nav>`, `<footer>`, `<aside>`, and `<header>` (configured via
`excluded_tags`), preserves headings as `#`/`##`/`###`, keeps code blocks
as fenced ` ``` ` blocks, and turns tables into pipe-delimited markdown
tables.

The output is already 90% of what I need. A small post-processing pass
strips tracking pixels and link-heavy leading paragraphs (typical
nav/footer leakage that survives the tag exclusion), and the file is
ready for chunking.

### API — markitdown's JSON converter

REST APIs return JSON. I convert JSON to markdown with
[markitdown](https://github.com/microsoft/markitdown):

```python
import io
import json
from markitdown import MarkItDown

_md = MarkItDown()

def _json_to_md(data: dict | list, title: str = "") -> str:
    stream = io.BytesIO(json.dumps(data, indent=2).encode())
    content = _md.convert_stream(stream, file_extension=".json").text_content
    return f"# {title}\n\n{content}" if title else content
```

A list of bank objects in JSON:

```json
[
  {"name": "GTBank", "code": "058", "currency": "NGN"},
  {"name": "Access Bank", "code": "044", "currency": "NGN"}
]
```

Becomes a structured markdown document with headings per entry and key/
value pairs as nested lists. The chunker can split on those headings,
and the model can read the result like any other documentation.

### Local docs — pymupdf4llm with markitdown fallback

PDFs are the trickiest source. Layout-heavy documents (multi-column
papers, tables, footnotes) need a layout-aware parser, but not every
parser handles every PDF. I use a two-strategy fallback:

```python
def _convert(input_file: str) -> str:
    ext = os.path.splitext(input_file)[1].lower()
    if ext == ".pdf":
        return _use_pymupdf4llm(input_file) or _use_markitdown(input_file) or ""
    return _use_markitdown(input_file) or ""
```

`pymupdf4llm.to_markdown()` handles columns, tables, and reading order
better than most alternatives. When it fails — and it does fail on edge
cases like scanned PDFs or unusual fonts — markitdown picks up the
slack. Either way, the output is markdown.

For everything else (DOCX, XLSX, CSV, PPTX, EPUB, audio transcripts,
images with OCR), markitdown is the single conversion path:

```python
def _use_markitdown(input_file: str) -> str | None:
    try:
        return MarkItDown().convert(input_file).text_content
    except Exception as e:
        print(f"  markitdown failed ({e})")
        return None
```

A 50-row Titanic CSV becomes a markdown table. A DOCX becomes headed
prose. An XLSX becomes a series of tables, one per sheet. The chunker
treats them all the same.


### The unifying frontmatter

Every ingester writes the same frontmatter on top of its markdown:

```yaml
---
path: https://developer.budpay.com/auth
title: Authentication
description: Authentication and access control
original_type: web
status_code: 200
crawled_at: 2026-04-30T08:14:22Z
---

# Authentication
...
```

Four sources, one shape. The chunker reads the frontmatter, the embedder
injects `title` + `description` + heading path into `embed_text`, the
retriever surfaces `path` and `title` as citations. The frontmatter is
the contract that lets four very different sources cohere into one
pipeline.

## What markdown gives the chunker

The chunker is where markdown pays its biggest dividend. Almost every
chunking pattern I use depends on markdown's structure being machine-
readable:

**Headers as natural split points.** I use
`MarkdownHeaderTextSplitter` to split documents into sections by `#`,
`##`, `###` before any character-level splitting kicks in. Sections
stay together. The header line goes into the chunk so the embedded
vector reflects what the section is *about*, not just what words it
contains. This is impossible without markdown.

**Code fences as atomic boundaries.** A regex on ` ``` ` lets me detect
code blocks and treat them as indivisible. A 1,500-character curl
example never gets split between `--data` and `'{...}'`. Plain text has
no equivalent — code looks like prose.

**Pipe-delimited tables as detectable units.** Markdown tables start
with `|`. A simple `line.strip().startswith("|")` check is enough to
detect a table block. The chunker then preserves the header row across
every table chunk so retrieval stays interpretable. JSON or HTML tables
would each need a different detector.

**Links as repairable patterns.** When a chunk boundary lands inside a
markdown link `[text](url)`, I detect the open `[` and unmatched `](`
and merge the chunks. Link integrity is preserved automatically. HTML's
`<a href="...">` would be far harder to match across a fragmentation
boundary.

**Navigation as filterable noise.** "Skip to content" links, link-only
lines, and footer link clouds all match small regexes against the
markdown shape. No HTML stripping, no DOM walking. A few patterns drop
the boilerplate.

If I'd kept the source as HTML, I'd be writing a parser. If I'd kept it
as plain text, I'd have lost every signal above. Markdown is the sweet
spot — structured enough to detect, simple enough to manipulate with
regex, readable enough that the LLM understands it natively at answer
time.

## What markdown gives retrieval

The chunker isn't the only beneficiary. Markdown's structure powers
two other stages.

**Heading-aware embed text.** When I embed a chunk, I prepend the page
title and the heading path:

```
API Basics
Authentication > Overview

Use a Bearer token in the Authorization header for every request.
```

The vector now encodes "this is about authentication", not just "this
mentions Bearer". This is only possible because markdown gave the
chunker a heading path to extract.

**Citations that point at structure.** When the chat agent answers a
question, it cites sources by `title` and `path` — both pulled from
frontmatter, both available because every source goes through the same
markdown+frontmatter contract. A user asks "where did this come from?"
and the answer is a clickable link, not a chunk hash.

**LLM-native rendering.** When the retrieved chunks go into the prompt,
they're already markdown. The model has been trained on enormous amounts
of markdown — it knows what `## Authentication` means, what a fenced
code block contains, and how to read a pipe-delimited table. There's no
translation layer. This isn't a small thing — every other format would
either lose structure or pay a tokenization tax.

## When markdown isn't enough

Markdown has limits. I won't pretend otherwise.

**Cell merges and complex tables.** Spreadsheets with merged cells,
spanning headers, or formula references lose information when flattened
to markdown tables. For corpora that depend on rich tabular semantics
(financial reports, scientific data), pure markdown isn't ideal —
you need a sidecar JSON or CSV.

**Footnotes and rich annotations.** PDFs with footnotes, endnotes, or
margin annotations get linearized awkwardly. Most markdown renderers
don't have a clean idiom for these, and most converters drop them.

**Equations.** Markdown via plain text loses LaTeX unless you preserve
`$...$` blocks deliberately. For math-heavy corpora, pick a parser that
emits LaTeX and treat those blocks as atomic, like code.

**Images with embedded text.** Markitdown can OCR images, but the
result is plain prose detached from where the image appeared. If
positioning matters, you need a richer format.

For my use case — payment-API documentation, developer guides, REST
responses, MCP resources — none of these limitations bite. For a legal
or scientific corpus, I'd reconsider.

## Takeaways

- **Pick the canonical format before anything else.** Every later stage
  has to respect it. Get this wrong and you pay forever.
- **Markdown is the cheapest format that preserves structure.** It's
  simpler than HTML, richer than text, parseable by regex, and natively
  understood by every modern LLM.
- **One format, four sources.** crawl4ai for the web, markitdown for
  JSON and documents, pymupdf4llm for PDFs, raw text for MCP. All write
  the same frontmatter+markdown shape.
- **Frontmatter is the contract.** Title, path, description, original
  type. That tiny header is what makes ingestion, chunking, embedding,
  retrieval, and citation cohere.
- **The chunker depends on markdown's structure.** Headers, fences,
  tables, links — every chunking pattern in the pipeline reads markdown
  syntax. Strip it and you lose the signal.

Markdown isn't fashionable. Nobody is writing think-pieces about it.
But every file in my RAG pipeline starts and ends as markdown, and that
quiet decision is doing more work than any model I've swapped in or
out. If you're starting a RAG, **pick your format first, and pick
markdown**.
