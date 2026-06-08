# REST Retrieval

SDK-backed retrieval route.

| Endpoint | SDK methods |
|---|---|
| `POST /v1/retrieve` | `RagRails(...).retrieve()` |

The server configures the SDK client from request fields, then calls retrieval.

Each response item includes `chunk_id`. Use this value for edit and delete
requests. It comes from stored chunk metadata when available and otherwise
falls back to the vector point id.
