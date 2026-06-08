# REST Embedding

SDK-backed embedding route.

| Endpoint | SDK methods |
|---|---|
| `POST /v1/embed` | `RagRails(...).embed()` |

The request body contains chunk dictionaries and provider configuration.
Responses return embedded chunk dictionaries in memory.
