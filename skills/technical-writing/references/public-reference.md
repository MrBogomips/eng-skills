# API, class, REST and OpenAPI reference

## Reference for one element

Write the contract, not the signature. For each function, method, type, endpoint or field, cover what applies:

| Part | Say |
|---|---|
| Summary | One sentence: what it does in domain terms. Not the name reworded ("Gets the user"). |
| Parameters | Meaning, unit, allowed range, default, what empty or null does |
| Result | What comes back, including the empty case |
| Errors | Each error or status code, and the condition that causes it |
| Guarantees | Idempotency, ordering, pagination, side effects, concurrency or thread safety, limits |
| Example | A minimal, correct call with its result |
| Lifecycle | Version it appeared in if the project tracks it, deprecation, provisional parts |

Describe only behaviour the code or the specification shows. If a guarantee is not there, don't promise it.

## REST and OpenAPI

- `summary`: a short verb phrase ("List orders"). `description`: behaviour, rules and guarantees, without repeating
  the summary.
- Document **every** response code the operation returns, errors included, each with its schema and an example.
- State authentication and the permission needed, pagination (how, page size, order), idempotency (keys, retries),
  rate limits and their headers.
- The published file holds no project references anywhere: descriptions, YAML comments, `x-` extensions, file name.
  The title and file name are descriptive ("Orders API", `orders.openapi.yaml`), not a module code.

## Error responses

An error the client receives is user text. Use the project's error format, or Problem Details (RFC 9457):

| Field | Content |
|---|---|
| `type` or `code` | Stable and machine-readable (`email-already-registered`). Clients branch on it, so never change it. |
| `title` | Short, the same for every occurrence of this error |
| `detail` | What happened to *this* request, and **what the client can do about it** |
| Status | The precise one: 409 for a conflict with existing state, 422 for a valid but unacceptable value |

```json
{
  "type": "https://api.example.com/problems/email-already-registered",
  "title": "E-mail address already registered",
  "status": 409,
  "detail": "The address ana@example.com is already registered. Sign in with it, or reset its password with POST /v1/password-resets."
}
```

Never put constraint, table, column, class or host names, stack traces or SQL in the body. Those go in the log.

## Deprecation and stability

- Use the ecosystem's own marker so tools pick it up: `[Obsolete]` (C#), `@deprecated` and `@Deprecated` (Java,
  TS), `// Deprecated:` paragraph (Go), `warnings.warn(..., DeprecationWarning)` plus a docstring note (Python),
  `deprecated: true` (OpenAPI) with `Deprecation` and `Sunset` headers.
- Always name the replacement and, if known, the removal version or date.
- Provisional behaviour (an open question in the project) is stated as such: "The page size is currently 50 and may
  become configurable; read it from the response instead of assuming it."

## Examples

- Use reserved values: `example.com` / `example.org` domains, `192.0.2.0/24` addresses, obviously fake keys
  (`sk_test_xxx`), invented names. Never real customer data, real hosts or working secrets.
- Examples must be correct for the current version. Prefer examples the build checks (doctests, example tests).

## Wording

Present tense, active voice ("Returns the orders", "You can cancel..."), one term per concept, the same as in the
API names and the UI, no marketing words: `register.md`.
