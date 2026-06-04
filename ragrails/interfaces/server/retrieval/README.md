# REST Retrieval

SDK-backed retrieval route.

| Endpoint | SDK methods |
|---|---|
| `POST /v1/retrieve` | `RagRails().embedder()`, `RagRails().retrieve()` |

The server creates provider objects from request config, then calls SDK
retrieval.
