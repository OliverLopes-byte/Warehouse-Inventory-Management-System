# Project learning preference

The user prefers slow, steady, beginner-friendly, technically accurate
explanations grounded in the current repository. Begin with theory and a small
diagram, then explain relevant source in execution order using concise code
snippets, define terms, trace related files as needed, and finish with a
recap/checkpoint. Teach one small topic at a time; do not overwhelm the user
with a whole service or the next topic unless they ask to continue.

For understanding the project or studying its files part by part, follow
[`docs/PROJECT_LEARNING_GUIDE.md`](../docs/PROJECT_LEARNING_GUIDE.md). The
recommended path is whole-project orientation, API Gateway, Auth, Catalog,
Warehouse, Reports, then cross-service flows and operations. Respect the
learner's pace and pause after each lesson.

When the user asks to explain, walk through, or trace an HTTP endpoint, follow
[`docs/ENDPOINT_LEARNING_PLAYBOOK_V2.md`](../docs/ENDPOINT_LEARNING_PLAYBOOK_V2.md).
A short prompt naming the method and path is sufficient. Include the relevant
imports, public and backend paths, Swagger inputs, route registration,
dependencies, validation, actual handler/helper flow, remote calls, database
work, response, and applicable errors. Use current source snippets and
line-linked file references.

Always inspect current source before explaining. The active application is
split across five services; older monolith walkthroughs and root `app/` links
are historical. Never claim authentication, authorization, database writes,
or other behavior that the selected route does not use. Do not execute
endpoints, mutate data, run migrations, or expose secrets just to explain
code.
