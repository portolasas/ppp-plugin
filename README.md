# ppp

ppp is an agent plugin for **VS Code (GitHub Copilot)** and **Claude Code** that builds Power Platform solutions with you: Power Automate flows, Power Apps canvas screens, SharePoint lists, Power BI reports and Copilot Studio prompts.

It works **offline from solution exports**. The agent has no tenant access, no connector and no live API. It reads the exported files, writes flow JSON, screen YAML and list schemas, checks them and packs an importable solution. Everything in the tenant (creating a scaffold, exporting, importing, testing) you do yourself, guided by short cards with the expected result.

A project can be **connected** to one environment (`ppp connect`). Then the agent fetches the export and imports the package itself, through the Power Platform CLI `pac` with your sign-in: each import after its checks (the right solution, unmanaged, a higher version, no change in the tenant it would overwrite), with a backup of the tenant's state, and after a card if you want one. It never imports into an environment of role production. Scaffolds, switching flows, connections, "paste code" and tests stay with you. Offline is the default.

## What you get
- **Agent `ppp`** with the core rules: questions as cards with a recommendation first, no silent assumptions, a commit after each confirmed step, stopping points with a model recommendation.
- **15 skills**, loaded when a task needs them:
  - phases: `ppp-intake`, `ppp-clarify`, `ppp-prototype`, `ppp-plan`, `ppp-package`, `ppp-diagnose`, `ppp-docs`, `ppp-golive`;
  - platform knowledge, each statement marked observed, documented, open or version-dependent: `ppp-power-automate`, `ppp-power-apps`, `ppp-sharepoint`, `ppp-power-bi`, `ppp-copilot-studio`;
  - `ppp-app-walk`: walks through your running app in Edge with automated clicks, reviews layout and usability from measurements and pictures, checks expected values and load times, reproduces errors, compares with the last run, and builds the illustrated Word handbook from its Markdown text, and training videos (optional packages `playwright`, `python-docx`).
  - `ppp-sessions`: on your request, uploads the session logs of your ppp projects to a private repository of yours, to improve ppp from them.
- **Command line `ppp`** (Python standard library only): unpack and pack solutions with `pac`, in a connected project export, import and read the tenant (`ppp connect`, `export`, `import`, `tenant`), inventory flows, check flows before packing (`ppp verify`, checks C1–C14), check screen YAML before "paste code" (`ppp canvas`), convert App.Formulas to de-DE, simulate flows, create project files from templates, record usage. `ppp --help` lists every command.
- **Hooks** for session start, turn end and compaction; they run only in ppp projects and never block. One more refuses a direct call of `pac` in a connected project, so that the tenant is reached through `ppp` and its checks only.

## Requirements
- VS Code with GitHub Copilot and agent plugins enabled, or Claude Code.
- Python 3.10 or newer. On Windows `python` must start it from `PATH` (installer option "Add python.exe to PATH"): the hooks and the tool call run `python`, and with only the launcher `py` both reach the placeholder of the Microsoft Store. `python --version` in a new terminal shows it.
- Power Platform CLI `pac` (in `PATH`, from the VS Code extension Power Platform Tools, or in `~/.dotnet/tools`). A connected project also needs pac signed in on the computer (`pac auth create`, once, by you).
- git. Each project chooses its storage at intake: a private GitHub repository, or a local folder without any server (git without a remote, backed up on request with `ppp backup` into a folder you choose, restored with `ppp restore`). Bitbucket is prepared.
- In VS Code a model that follows the agent text: GPT-6.1 Sol for building, Claude Opus 5.5 for clarification, planning and diagnosis. Not GPT-6 Luna. GPT models with the small context size (272k) in the model picker: the long context costs double above 272k; Claude models cost the same in both.

## Quick start

### 1. Install
**VS Code.** No JSON editing and no install script:
1. Add the marketplace: open the Settings, search for `chat.plugins.marketplaces`, choose "Add Item" and enter `portolasas/ppp-plugin`. Or in the Agents view: Customizations › Browse › Configure Marketplaces › Add Marketplace.
2. Install **ppp** from the marketplace (Customizations › Browse, or the Extensions view under Agent Plugins) and confirm the trust prompt.
3. Run "Developer: Reload Window" and choose the agent **ppp** once in the agent picker; it stays chosen.

If ppp does not appear, check that agent plugins are on (`chat.plugins.enabled`).

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
project.json          name, prefix, modules, mode, storage, solutions
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
ppp keeps everything in your project folder and its git repository. Exports can contain personal data and tenant details; keep project repositories private, or choose the local folder, which stores no project data on GitHub. Backups of a local project go only to the folder you set (`ppp settings --backup <folder>`). The plugin itself holds no tenant, personal or customer data. Session logs leave the computer only when you ask for an upload, only to the repository you name (`ppp settings --sessions <clone>`), and only for projects on GitHub; keep it private.

## More
- [CHANGELOG.md](CHANGELOG.md): versions and changes.
- [THIRD_PARTY.md](THIRD_PARTY.md): adopted templates, their licences, and the icon.
