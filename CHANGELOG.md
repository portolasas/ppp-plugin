# Changelog

Versions of the ppp plugin, newest first. Every published change raises at least the patch version and names here what changed; a learning session adds the lesson IDs as evidence (archive `knowledge/lessons/` in the ppp repository).

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
