---
name: ppp-power-apps
description: Platform knowledge for Power Apps canvas apps - screens as YAML for "paste code", Power Fx notation de-DE and en-US, App.Formulas theme, control versions, runtime behaviour, delegation and performance, layout of classic controls, generators. Use before building, changing, checking or diagnosing a screen or formula.
---

# Power Apps (canvas)

Status per statement: **[B]** observed in the tenant, **[D]** documentation, not yet confirmed here, **[O]** open, **[V]** version-dependent. Lesson IDs name the evidence.

## Always
1. Screens reach the app as YAML by "paste code"; the `.msapp` in a solution is never edited, the app is not in the package (A-7). [B]
2. YAML formulas in en-US; formula bar and App.Formulas in the user's Studio notation, de-DE from `ppp formulas`. Every instruction names the notation. [B]
3. Control versions only from a probe (`versionen.py`), never guessed. [B]
4. Colours only through theme roles (`BIRole`, `BIColor`, `BIFont`, `BISize` in App.Formulas; brand values from the skill bi-designer). [B]
5. Before a screen goes to the user: `ppp canvas` ends with RESULT: OK, every warning explained.
6. Permission checks run in the flow, not in the app. [B]

## References
| Topic | File |
|---|---|
| Change path, notation de-DE and en-US | [references/notation.md](references/notation.md) |
| YAML for "paste code", control versions, generators and the central blocks, `ppp canvas` | [references/yaml.md](references/yaml.md) |
| Runtime: start, navigation, flow calls, errors, Monitor, Dataverse roles | [references/behaviour.md](references/behaviour.md) |
| Performance and delegation with SharePoint and flows | [references/performance.md](references/performance.md) |
| Layout, auto layout, classic control colours, theme, media, timelines | [references/layout.md](references/layout.md) |
| App state in a solution export | [references/solution.md](references/solution.md) |
