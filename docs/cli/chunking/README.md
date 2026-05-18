# CLI Chunking

Chunking commands split markdown files into chunk JSON files.

## Commands

| Command | Description |
|---|---|
| `ragrails chunk` | Split a folder of markdown files into chunk JSON files |
| `ragrails chunk-file` | Preview chunks for one markdown file |

## chunk

```bash
ragrails chunk --input-dir files/output/api --output-dir files/output/chunks/api
```

Options:

| Option | Default | Description |
|---|---|---|
| `--input-dir` | `files/output/web_crawled` | Folder containing markdown files |
| `--output-dir` | `files/output/chunks` | Folder where chunk JSON files are written |
| `--chunk-size` | `2000` | Target maximum chunk size |
| `--chunk-overlap` | `200` | Overlap between chunks |
| `--min-chunk-length` | `100` | Minimum chunk length to keep |

## chunk-file

Preview chunks for one markdown file without writing the full folder output:

```bash
ragrails chunk-file files/output/docs/guide.md
```

Options:

| Option | Default | Description |
|---|---|---|
| `--chunk-size` | `2000` | Target maximum chunk size |
| `--chunk-overlap` | `200` | Overlap between chunks |
| `--min-chunk-length` | `100` | Minimum chunk length to keep |

Back to the [CLI overview](../README.md).
