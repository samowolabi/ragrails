# REST Storing

SDK-backed storage lifecycle routes.

| Endpoint | SDK method |
|---|---|
| `POST /v1/store` | `RagRails().store()` |
| `POST /v1/edit` | `RagRails().edit()` |
| `POST /v1/delete` | `RagRails().delete()` |

Lifecycle operations are chunk-level and vector database agnostic.
