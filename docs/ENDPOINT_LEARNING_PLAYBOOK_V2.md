# Endpoint Learning Playbook — Version 2

## Purpose and audience

Use this playbook when the learner asks to explain one HTTP endpoint in the
current Warehouse Inventory **microservices** project. The goal is to teach
the endpoint carefully, from its theory and public URL through actual Python
execution and the response, without assuming the learner already knows
FastAPI, HTTP, SQLAlchemy, PostgreSQL, JWT, or service-to-service calls.

Version 2 adopts the learner's preferred style: a real tutorial with
background concepts, a diagram, small current code excerpts, execution order,
and a recap. It is intentionally not a terse route summary.

For understanding a whole service or studying files one by one, use
[`PROJECT_LEARNING_GUIDE.md`](./PROJECT_LEARNING_GUIDE.md) instead.

## Non-negotiable accuracy rules

1. Re-read current source before explaining. This project has been migrated
   from a monolith; do not rely on old examples that refer to the removed root
   `app/`, root models, root routers, or root migrations.
2. Follow the actual route registration and caller path. In this application,
   the Gateway adds a public service prefix while backend route decorators
   define service-local paths. Explain both names where they differ.
3. Describe only checks, dependencies, service calls, SQL, and writes that
   the chosen endpoint actually uses. Say explicitly when authentication,
   authorization, a database write, or a remote call is not used.
4. Explain the actual implementation, not only the intended design. If code
   and handoff disagree, point out the difference and ground behavior in code.
5. Keep unrelated endpoints and imports out of the explanation. Follow helpers
   only as far as needed to complete this endpoint's trace.
6. Do not call the endpoint, mutate data, run migrations, or test a live
   database just to explain it. The learner can request an execution
   separately.
7. Never expose real secrets, passwords, bearer tokens, or local `.env`
   contents. Use invented examples.
8. Use concise snippets from the actual source, with links to the current
   source files and line numbers. Do not paste entire files.
9. Explain failure behavior from the actual code and framework behavior; do
   not invent response codes.
10. Pace the response. Cover the endpoint fully, but do not continue into the
    next endpoint or service without being asked.

## The mental model

Start with the smallest diagram that accurately represents the endpoint:

```text
Browser / API client
    |
    | public URL, optional bearer token, request body/query
    v
API Gateway (port 8000)
    |
    | strips /api/<service> prefix and forwards selected headers/body
    v
Owning service route
    |
    +--> FastAPI dependencies: input/auth/role/session (only if declared)
    +--> local helpers and HTTP clients (only if called)
    +--> service-owned PostgreSQL database (only if used)
    |
    v
Handler result -> response schema/serialization -> Gateway -> caller
```

For service-to-service authentication and Catalog reference checks, draw only
the calls that the endpoint actually makes. Gateway routing is not the same
thing as endpoint business logic. A cross-service HTTP call is not a
cross-database transaction.

## Teaching sequence for one endpoint

Use the following sections in order. Combine adjacent sections only when the
endpoint is very small; do not omit a section just because the answer is
written in a beginner-friendly style.

### 1. Lesson goal and plain-language purpose

In a few sentences:

- State the real-world task the endpoint performs.
- Identify its owning service and whether it reads, writes, or both.
- Tell the learner what they should understand by the end.

Define new terms before relying on them.

### 2. Theory before code

Explain the relevant concepts in simple language. Select only what applies,
for example:

- HTTP method and resource path.
- Request body versus path/query/header input.
- Authentication versus authorization.
- Database read versus database transaction.
- Local ownership versus remote service lookup.
- Idempotency, locking, or append-only history for relevant mutations.

Use a small analogy if it helps, then state where the analogy stops matching
the actual implementation.

### 3. Where it sits in the project

Show the endpoint's position in the service and one small data-flow diagram.
Name only the files needed to understand it, such as:

```text
Gateway route
   -> service router handler
   -> dependency/client/helper
   -> model and owning database (if applicable)
   -> response schema
```

Identify whether a file runs at process startup or while an HTTP request is
being handled.

### 4. Exact route and Swagger operation

State:

- Public URL through the Gateway.
- Backend service-local method and path.
- Owning service and Swagger tag.
- How the Gateway prefix combines with the router prefix and decorator path.
- Whether a request should use **Authorize**.

Inspect the current Gateway and app/router registration. Do not assume the
public path equals the backend path. If current paths have surprising
duplication or naming, explain the exact composition without silently
correcting it.

Explain the relevant Swagger controls:

- **Try it out** opens editable fields.
- **Execute** sends the HTTP request.
- **Authorize** stores credentials for protected calls in Swagger; it does not
  itself run the endpoint.

### 5. Imports and the endpoint's vocabulary

Show only the important imports from the handler and the directly used
dependencies/helpers. Explain libraries in context, for example:

- FastAPI router/decorator/dependency.
- Pydantic request or response schema.
- SQLAlchemy session/query/model.
- `httpx` client for a remote service.
- JWT/OAuth bearer dependency when used.

For each imported project symbol, say which file defines it and why this
endpoint needs it. Do not explain neighboring imports that the selected
handler does not use.

### 6. Route registration and handler signature

Show a short, exact snippet from:

- The service's `app/main.py` router registration.
- The endpoint decorator and function signature.
- The Gateway prefix/proxy only if needed to establish the public URL.

Explain what the decorator registers and what the function parameters mean.
Clarify that registration happens during application setup; it is not the
request itself.

### 7. Request shape and validation

List the endpoint's actual inputs:

| Input location | Field | Type/constraint | Where declared |
|---|---|---|---|
| Body / path / query / header | Current field | Current validation | Schema or route |

Then show one invented, safe request example in the right content type:
JSON, form-encoded data, path/query values, or headers. Explain whether
FastAPI/Pydantic validates it before entering the handler and what happens
when validation fails.

Do not list OAuth2 optional form fields as business inputs unless the handler
actually reads them.

### 8. Dependencies, authentication, authorization, and scope

Trace FastAPI dependency resolution before handler execution:

```text
request field
  -> dependency alias
  -> dependency function
  -> current user/role/session/client value
  -> handler parameter
```

For only the checks actually used, explain:

- How the bearer token is extracted and validated.
- Whether identity is validated locally or through Auth introspection.
- Which service credential protects an internal call.
- Which role is permitted.
- How home-warehouse scope is obtained and enforced.
- How a database session or configuration object is injected.

Explicitly say “this endpoint does not use …” for a tempting but absent check.
Never infer the actor's role or ID from an untrusted request body.

### 9. Handler execution, one step at a time

Show short current snippets in the order they execute. For each block:

1. State what value enters the block.
2. Explain what the expression or function call does.
3. State what value/result it produces.
4. Explain the next branch, helper, remote call, query, or error.

Follow a helper into another file if it is required to understand behavior.
Stop before unrelated helper internals. Mark the difference between:

- Validation performed by FastAPI before the function.
- Business validation inside the handler/helper.
- Database constraints enforced only when SQL is executed or committed.

### 10. Remote-service calls, when present

Trace each actual HTTP call:

- Which client module issues it.
- Which service and internal endpoint it calls.
- What headers/parameters are sent (describe secrets without revealing them).
- How timeout/network/HTTP/invalid-response cases are mapped.
- Whether missing references become 404, 422, or another status.

Explain that a successful remote lookup validates a reference but does not
create a database foreign key across service-owned databases.

### 11. Database and transaction path, when present

Show the relevant model/table and the actual SQLAlchemy operations. Explain:

- What is read, inserted, updated, or archived.
- Where a row lock is acquired, if any.
- Where `flush`, `commit`, or rollback happens.
- Which changes share one transaction.
- Which remote work occurs outside that transaction.
- Important database constraints or ledger rules relevant to this endpoint.

Distinguish the SQLAlchemy session, transaction, engine/connection, and
PostgreSQL in beginner terms. If there is no database work, state that clearly.

### 12. Response construction and what the caller sees

Show the actual response model and a small representative response. Explain:

- Which Python object/value is returned.
- How the response model validates/filters/serializes it.
- HTTP success status and relevant response headers.
- What Swagger displays.
- How an authentication response is used on the next protected request,
  when relevant.

Do not claim exact response fields without checking the current schema.

### 13. Failure paths and practical effect

Use a concise table:

| Condition | Actual source/check | Result |
|---|---|---|
| Invalid input | Schema or handler | Verified status |
| Unauthenticated/forbidden | Relevant dependency | Verified status |
| Missing reference/row | Relevant helper | Verified status |
| Conflict/constraint | Business rule/database handler | Verified status |
| Required service unavailable | HTTP client | Verified status |

Include only applicable rows and statuses verified in current code. Explain
what durable state changes on success and how a read endpoint could verify it,
without actually executing a mutation.

### 14. Full flow, recap, and learner checkpoint

Finish with:

1. A short numbered request-to-response flow.
2. A beginner recap in plain language.
3. A mini-glossary of newly introduced terms.
4. Two or three self-check questions.
5. A useful next endpoint or source file, clearly marked optional.

Pause after the selected endpoint. Do not start the next topic automatically.

## How to handle different endpoint types

### Read-only endpoint

Emphasize filters, sorting, pagination, role/warehouse scope, query execution,
response mapping, and whether it makes remote lookups. Do not describe a
commit or write if none occurs.

### Create/update/archive endpoint

Explain validation, duplicate/reference rules, soft deletion versus physical
deletion, commit location, resulting state, and a safe read that would verify
the result. Do not call it during the explanation.

### Authentication endpoint

Distinguish account password, password hash, JWT signing secret, bearer token,
and service-to-service token. Explain exact form/JSON behavior and token
claims. Trace the next request only far enough to explain how the token is
used.

### Warehouse movement/receipt endpoint

Trace warehouse scope, remote Catalog checks, row locks, nonnegative-stock
rules, balance changes, ledger rows, and commit count. Explain precisely
which writes are atomic inside Warehouse and which remote reads happen
outside that transaction.

### Reports endpoint

Explain role requirements, remote read sources, page/batch limits, calculation
logic, error behavior, and the absence of a persistent report database or
cross-service snapshot if confirmed by current source.

## How the learner can ask

Any short request naming method and path is sufficient:

> Explain `POST /api/warehouse/stock/issue` slowly, one part at a time.

The assistant should resolve the real Gateway URL and backend route from
source, then follow this playbook. To pause or change depth, the learner can
say:

- “Pause and explain that term.”
- “Go deeper into the SQL transaction.”
- “Show only the next section.”
- “Give me a recap before we continue.”

No extra credentials, real tokens, database URLs, or secret values are needed.

