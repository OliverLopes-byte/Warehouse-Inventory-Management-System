# Endpoint learning

When the user asks to explain, walk through, or trace an HTTP endpoint (for
example, "Explain `GET /products` end to end"), automatically follow
[`docs/ENDPOINT_LEARNING_PLAYBOOK.md`](../docs/ENDPOINT_LEARNING_PLAYBOOK.md).
A short prompt naming the method and path is sufficient; do not require the
user to repeat the playbook's format.

Use the playbook's combined beginner-friendly format in the first answer:
explain the relevant imports/libraries, Swagger inputs and actions, route
decorator and app registration, dependencies/configuration, validation,
handler code in execution order, helper calls across files, database work,
response schema, practical result, and relevant errors. Include concise,
current code snippets in the sections they explain, with links to the source
files and line numbers. Do not give only a high-level overview and wait for a
follow-up asking for snippets.

Inspect the current source before explaining. Adapt the flow to the endpoint:
do not describe authentication, authorization, a database write, or any other
step as occurring unless that route actually uses it. Do not execute the
endpoint or change data unless the user explicitly asks.
