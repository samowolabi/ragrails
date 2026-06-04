# REST Chat

SDK-backed chat route.

| Endpoint | SDK method |
|---|---|
| `POST /v1/chat` | `RagRails().chat()` |

REST chat is stateless. Pass `history` in the request and persist the returned
`history` in the client application.
