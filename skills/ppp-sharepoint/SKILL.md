---
name: ppp-sharepoint
description: SharePoint lists of a solution - list design, field XML, components/sharepoint/schema.json, the setup flow, REST write patterns, indexes, threshold and permissions. Use before creating or changing lists, columns, start values or the setup flow.
---

# SharePoint

Status per statement: **[B]** observed in the tenant, **[D]** documentation, not yet confirmed here, **[O]** open, **[V]** version-dependent. Lesson IDs name the evidence.

## Always
1. `components/sharepoint/schema.json` is the source of every list; lists change only through it and a run of the setup flow `<prefix>_Setup` (ANFORDERUNGEN T3). `components/sharepoint/README.md` is the inventory for people.
2. Every list carries the project prefix (`ASUM_Rollen`). [B]
3. Users read; only flows write, through a connection account with edit rights. The role check runs in the flow over `x-ms-user-email`. [B]
4. Times are stored and computed in UTC; converted only for display. [B]

## References
| Topic | File |
|---|---|
| Designing lists, field XML, indexes and threshold, permissions, evidence by "CSV with schema" | [references/lists.md](references/lists.md) |
| `schema.json`, `ppp schema`, `ppp setupflow`, phases, tests of the setup flow | [references/setup-flow.md](references/setup-flow.md) |
| REST write patterns: MERGE, ETag, run ID, reading the schema | [references/rest.md](references/rest.md) |

Reading items and files from flows (Get item, Get file content, file triggers): skill ppp-power-automate, `references/sharepoint-connector.md`. Delegation in apps: skill ppp-power-apps.
