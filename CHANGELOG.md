# Changelog

Versions of the ppp plugin, newest first. Every published change raises at least the patch version and names here what changed; a learning session adds the lesson IDs as evidence (archive `knowledge/lessons/` in the ppp repository).

## 0.4.2 (2026-10-29)
- README and ppp setup: install in VS Code by adding the marketplace portolasas/ppp-plugin in the Settings (chat.plugins.marketplaces › Add Item) or under Customizations › Configure Marketplaces, no JSON editing (user, 2026-10-29).

## 0.4.1 (2026-10-28)
- Presentations: ppp-clarify reads a deck through its slide description <name>.md (bi-design 2.3.0) instead of the PPTX; ppp-docs prepares every deck as a slide description, the template bi-ppt takes as "dokument"; ppp-intake keeps a presentation together with its slide description (T6, user, 2026-10-28).

## 0.4.0 (2026-10-27)
- wdl_sim fails like the tenant on property names with . [ or ] in setProperty and addProperty (PA-20261026-WIN-01) and on startsWith/endsWith with an object or array (PA-20261026-WIN-02); ppp verify C9 reports literal names. Two runs that passed locally had failed in the tenant (Orga-Otto package 003).
- Knowledge: hyperlink columns read through REST are objects {Url, Description}, Get items returns text (SP-20261026-WIN-01; corrects lists.md and sharepoint-connector.md).
- ppp-diagnose: without a platform error text in the report the first card asks for the error message of the first failed action; a lesson proposal for an unknown platform cause belongs to the done criterion of step 4.
- Core rules: cards ask in text fields for no times, counts or other evidence; every progress line in the user's language; the stopping point recommends GPT-6.1 Sol also for building a prototype or document; known misfire: Outlook COM hangs on .msg files.
- ppp check names local leftovers without files; ppp tidy --leftovers removes them bottom-up, read-only folders too, links never followed (GEN-20261025-WIN-01).
- ppp mail reads an Outlook .msg without Outlook: subject, sender, recipients, date, body (text, else HTML), attachments numbered on equal names (GEN-20261026-WIN-01).
- ppp-prototype: screenshots in desktop width with Edge headless (GEN-20261026-WIN-02, GEN-20261027-WIN-01).
- ppp verify --allowed accepts a file name that matches exactly one changed file (SOL-20261025-WIN-01).

## 0.3.0 (2026-10-27)
- Skill ppp-sessions and command ppp sessions (PLUGIN PL-20, user, 2026-10-27): on request, the Copilot session logs of ppp projects that changed since the last upload of this computer go to the clone of the user's private sessions repository (copy, commit, push); ppp settings --sessions <clone> keeps its folder, ~/.ppp/sessions.json the time of the last upload.

## 0.2.2 (2026-10-25)
- README with a quick guide: what ppp is, requirements, installation in VS Code and Claude Code, first project, package cycle, updates, project layout (user, 2026-10-25).

## 0.2.1 (2026-10-25)
- ppp-package step 1: after the confirmed proposal a one-line hint that GPT-6.1 Sol is enough for building (proposal and design often run on Claude Opus 5.5; no stopping point prompts the switch otherwise, A-9; Orga-Otto package 003).

## 0.2.0 (2026-10-25)
- Structure A (PLUGIN PL-4, PL-5, PL-17, PL-18, changed 2026-10-25): the agent ppp comes with the plugin (com.github.copilot/agents/ppp.agent.md), a second manifest plugin.json after Agent Plugins 1.0 for VS Code, hooks for VS Code in com.github.copilot/hooks/hooks.json.
- Hooks: each hook file names its tool (copilot, claude); SessionStart gives VS Code additionalContext at the top level (the agent host dropped hookSpecificOutput, installation retest 4) and keeps the tool call in ~/.ppp/tool-call.txt.
- Core rules: the tool call comes from the session context, without hooks from ~/.ppp/tool-call.txt or the newest tools/ppp.py under VS Code's agentPlugins; no placeholder.
- ppp setup removes the agent copy of earlier versions (~/.copilot/agents/ppp.agent.md), which would hide the plugin agent, and shows the installation entries; ppp check reports such a copy; the version stands in four places.
- Author Pascal Naumann in both manifests; icon .claude-plugin/icon.png from the Boehringer Ingelheim icon set.

## 0.1.2 (2026-10-25)
- Core rules and model recommendation: never GPT-6 Luna for ppp, it does not follow the agent text reliably (installation retest 4, 2026-10-25); on GPT-6 Luna the agent recommends GPT-6.1 Sol. Known misfire on patch edits no longer names Luna.

## 0.1.1 (2026-10-25)
- ppp check updates the ppp clone at the start of a session (git pull --ff-only when it is behind its upstream and has no local changes or commits) and renews the agent copy; otherwise it warns as before (AKTUALISIEREN.md).

## 0.1.0 (2026-10-24)
- Transfer solution in mode large (user, 2026-10-24): role transfer in project.json, ppp unpack registers <prefix>Transfer, inventory, verify, pack and setupflow default to it; ppp-package step 2 sets its members, ppp-golive packs the main solution.
- ppp tidy at package close: the imported package with its report goes to exchange/archive/, intermediate packages and older exports are deleted, other files are listed for a card (user, 2026-10-24).
- Core rules: clear what ppp check reports first, deleting only after a card. ppp check names folders outside git as local leftovers, asks to keep the STATE.md headings and warns when the ppp clone is behind its upstream.
- ppp archive moves the package folder itself when git mv is denied (SOL-20261024-WIN-01).
- Checks: C9 property names with a leading @ (PA-20261024-WIN-01); C7 and wdl_sim reject createArray() without arguments (PA-20261024-WIN-02); ppp canvas reports .Value <> in filters, SearchItems on combo boxes and filters that read no list of the source pattern (PAPPS-20261024-WIN-01).
- Knowledge: Until loops (PA-20261023-WIN-01), SharePoint Accept format and both ETag spellings (PA-20261021-WIN-01, PA-20261022-WIN-01), chips in rows of labels (PAPPS-20261021-MAC-01); archived as incorporated in 0.0.2: GEN-20261021-WIN-01, SOL-20261021-WIN-01.

## 0.0.2 (2026-10-23)
- Hooks run in VS Code where the agent host runs them; the IT allows it (PLUGIN PL-16 changed). SessionStart leaves out the core rules there, the agent ppp brings them.
- Core rules: "All as expected" or the user's own report confirms a step with its checks (GEN-20261021-WIN-01); commit and push after each step that changed files; STATE.md only at stopping points, on a package change and for a temporary tenant state; a card ends every turn that hands over to the user; a stopping-point card after a break; ppp check at the start of a session; known misfire: group policy blocks virtual environments.
- ppp-package: the checks after the import stand on the import card; a version not raised yet is only a hint in step 4. ppp-diagnose starts with the error message and the local definition and asks for exports only for an open question.
- Tools: pac is also found in the VS Code extension Power Platform Tools and in ~/.dotnet/tools; ppp unpack unpacks into a temporary folder first and removes read-only folders (SOL-20261021-WIN-01); file errors as one ERROR line; ppp check creates a missing exchange/; ppp run names a missing package with the pip command; ppp verify reports C5 only as a hint; ppp --help shows every command with its options; ppp new names the lesson areas.
- Templates: STATE.md and AGENTS.md hold no running status.

## 0.0.1 (2026-10-20)
- First build: command line `ppp` (solution, canvas, setup-flow, project-structure and usage tools with the central building blocks), core rules `core/ppp.agent.md`, hooks for Claude Code, eight phase skills and five module skills with the consolidated platform knowledge.
