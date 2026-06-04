# REST Chunking

SDK-backed chunking route.

| Endpoint | SDK method |
|---|---|
| `POST /v1/chunk` | `RagRails().chunk()` |

Request bodies pass markdown strings or document dictionaries. Responses return
chunk dictionaries in memory.
