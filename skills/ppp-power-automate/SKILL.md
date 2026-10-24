---
name: ppp-power-automate
description: Platform knowledge for Power Automate cloud flows - workflow JSON, expressions, designer behaviour, triggers, child flows, SharePoint connector, Teams and Outlook. Use before building, changing, diagnosing or describing a flow.
---

# Power Automate

Knowledge with a status per statement: **[B]** observed in the tenant, **[D]** Microsoft documentation, not yet confirmed here, **[O]** open, **[V]** version-dependent, re-check after Microsoft updates. Never present [O] as fact. Lesson IDs name the evidence (archive `knowledge/lessons/` in the ppp repository).

## Always
1. Internal names of triggers, actions, columns and inputs come from the code view or an export, never from memory. [B]
2. A flow is planned completely before building: every action, every connector, every missing tenant fact asked in one round. [B]
3. Connector actions and child-flow bindings come from actions the designer saved (scaffold, another flow), never written by hand. [B]
4. Conditions only in structured form; fixed text first in URI, filter and order-by fields; no `Terminate` inside loops; nesting at most level 8. `ppp verify` checks these.
5. Errors stay visible: Try/Catch/Finally with status and error text in the record, no silent fallback. Writes are idempotent with a stable key from the source. [B]
6. After an import the user decides whether a flow is on; the package state does not decide it. [B]

## References
| Topic | File |
|---|---|
| Designer: conditions, text fields, scaffolds, saving, run control | [references/designer.md](references/designer.md) |
| Expressions: missing functions, JSON bodies, variables, reading outputs | [references/expressions.md](references/expressions.md) |
| Structure: scopes, runAfter, nesting, loops, child flows, retry, idempotency, test helpers | [references/structure.md](references/structure.md) |
| Triggers: Power Apps V2, environment variables, SharePoint and file triggers, Teams | [references/triggers.md](references/triggers.md) |
| SharePoint connector and REST from flows, files | [references/sharepoint-connector.md](references/sharepoint-connector.md) |
| Teams, Outlook, Graph | [references/teams-outlook.md](references/teams-outlook.md) |
| Error message → cause → fix, and the checks of `ppp verify` | [references/errors.md](references/errors.md) |
