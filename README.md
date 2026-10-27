# ppp

ppp is an agent plugin for **VS Code (GitHub Copilot)** and **Claude Code** that builds Power Platform solutions with you: Power Automate flows, Power Apps canvas screens, SharePoint lists, Power BI reports and Copilot Studio prompts.

It works **offline from solution exports**. The agent has no tenant access, no connector and no live API. It reads the exported files, writes flow JSON, screen YAML and list schemas, checks them and packs an importable solution. Everything in the tenant (creating a scaffold, exporting, importing, testing) you do yourself, guided by short cards with the expected result.

## What you get
- **Agent `ppp`** with the core rules: questions as cards with a recommendation first, no silent assumptions, a commit after each confirmed step, stopping points with a model recommendation.
- **14 skills**, loaded when a task needs them:
  - phases: `ppp-intake`, `ppp-clarify`, `ppp-prototype`, `ppp-plan`, `ppp-package`, `ppp-diagnose`, `ppp-docs`, `ppp-golive`;
  - platform knowledge, each statement marked observed, documented, open or version-dependent: `ppp-power-automate`, `ppp-power-apps`, `ppp-sharepoint`, `ppp-power-bi`, `ppp-copilot-studio`;
  - `ppp-sessions`: on your request, uploads the session logs of your ppp projects to a private repository of yours, to improve ppp from them.
- **Command line `ppp`** (Python standard library only): unpack and pack solutions with `pac`, inventory flows, check flows before packing (`ppp verify`, checks C1–C14), check screen YAML before "paste code" (`ppp canvas`), convert App.Formulas to de-DE, simulate flows, create project files from templates, record usage. `ppp --help` lists every command.
- **Hooks** for session start, turn end and compaction. They run only in ppp projects and never block.

## Requirements
- VS Code with GitHub Copilot and agent plugins enabled, or Claude Code.
- Python 3.10 or newer.
- Power Platform CLI `pac` (in `PATH`, from the VS Code extension Power Platform Tools, or in `~/.dotnet/tools`).
- git; a GitHub repository per project is recommended.
- In VS Code a model that follows the agent text: GPT-6.1 Sol for building, Claude Opus 5.5 for clarification, planning and diagnosis. Not GPT-6 Luna.

## Quick start

### 1. Install
**VS Code.** Add to your user settings (JSON):
```json
"chat.plugins.enabled": true,
"chat.plugins.marketplaces": ["portolasas/ppp-plugin"]
```
Install **ppp** in the Extensions view under Agent Plugins, run "Developer: Reload Window" and choose the agent **ppp** once in the agent picker; it stays chosen.

**Claude Code.** Once per computer:
```
/plugin marketplace add portolasas/ppp-plugin
/plugin install ppp@ppp
```
Then start a new session.

### 2. Start a project
Open a folder for the project and tell the agent what you want, for example:
- "New solution: an app to request training slots, with an approval flow."
- "Take over the existing solution; the export is in `exchange/`."

The agent asks name, prefix, modules, mode (small, medium, large) and handbook language on one card and creates the project with `ppp init`. For an existing solution it unpacks the export, inventories every flow and drafts the specs.

### 3. Work in packages
1. **Clarify** the requirements in card rounds (`specs/`, `decisions/`), optionally with a click prototype.
2. **Plan** packages in `ROADMAP.md`.
3. **Build** each package in `changes/NNN-name/`: you confirm the proposal, the agent builds and checks offline, packs the solution into `exchange/`, you import it and test the critical scenarios on cards. App screens reach Power Apps Studio by "paste code".
4. **Go live**: full test, move to test and production, hypercare.

After a break the agent continues from `STATE.md`.

### 4. Updates
VS Code fetches new versions itself (with `extensions.autoUpdate`, about every 24 hours); reload the window afterwards. In Claude Code:
```
/plugin marketplace update ppp
/plugin uninstall ppp@ppp
/plugin install ppp@ppp
```
What changed is in [CHANGELOG.md](CHANGELOG.md).

## Project layout
```
project.json          name, prefix, modules, mode, solutions
STATE.md              where the work stands; read first in every session
AGENTS.md             project rules for the agent
ROADMAP.md            all packages with goal and status
specs/, decisions/    confirmed requirements and decisions
changes/NNN-name/     one folder per package (proposal, tasks); finished ones in changes/archive/
solution/<Name>/      working copy of the solution (pac unpack format)
components/<module>/  inventory, screens, list schema, flow documents, generators
exchange/             exports in, packages out (not in git)
inputs/, docs/, ...   material as handed over; handbook and training; created when needed
```

## Data
ppp keeps everything in your project folder and its git repository. Exports can contain personal data and tenant details; keep project repositories private. The plugin itself holds no tenant, personal or customer data. Session logs leave the computer only when you ask for an upload, and only to the repository you name (`ppp settings --sessions <clone>`); keep it private.

## More
- [CHANGELOG.md](CHANGELOG.md): versions and changes.
- [THIRD_PARTY.md](THIRD_PARTY.md): adopted templates, their licences, and the icon.
