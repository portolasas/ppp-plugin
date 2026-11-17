# ppp

ppp is an agent plugin for **VS Code (GitHub Copilot)** and **Claude Code** that builds Power Platform solutions with you: Power Automate flows, Power Apps canvas screens, SharePoint lists, Power BI reports and Copilot Studio prompts.

This repository is a marketplace with three plugins. You choose which ones you install:

| Plugin | What it is | Needed |
|---|---|---|
| **ppp** | the agent `ppp`, 15 skills, the command line `ppp` and its hooks | yes |
| **bi-design** | the corporate design of Boehringer Ingelheim for agents: skill `bi-designer`, agent `bi-ppt` and generator `bippt` for PowerPoint | optional |
| **bi-deneb** | Deneb visuals for Power BI in the brand design: skill and agent `bi-deneb`, generator `bideneb` | optional |

All three are released together and carry one version.

## How ppp works
It works **offline from solution exports**. The agent has no tenant access, no connector and no live API. It reads the exported files, writes flow JSON, screen YAML and list schemas, checks them and packs an importable solution. Everything in the tenant (creating a scaffold, exporting, importing, testing) you do yourself, guided by short cards with the expected result.

A project can be **connected** to one environment (`ppp connect`). Then the agent fetches the export and imports the package itself, through the Power Platform CLI `pac` with your sign-in: each import after its checks (the right solution, unmanaged, a higher version, no change in the tenant it would overwrite), with a backup of the tenant's state, and after a card if you want one. It never imports into an environment of role production. It creates the first, empty solution with your publisher after a card, adds the members of the transfer solution (membership only), and reads the runs of the project's flows with their errors. Every card names a code, and the agent goes on only with that code: your answer holds for the state you saw. One call against the tenant runs at a time. A hook stops a direct pac call by mistake; it is no barrier against intent. Scaffolds, switching flows, connections, "paste code" and tests stay with you. Offline is the default.

## What you get with ppp
- **Agent `ppp`** with the core rules: questions as cards with a recommendation first, no silent assumptions, evidence before claims, a commit after each confirmed step, stopping points with a model recommendation.
- **16 skills**, loaded when a task needs them:
  - phases: `ppp-intake`, `ppp-clarify`, `ppp-prototype`, `ppp-plan`, `ppp-package`, `ppp-diagnose`, `ppp-docs`, `ppp-golive`;
  - platform knowledge, each statement marked observed, documented, open or version-dependent: `ppp-power-automate`, `ppp-power-apps`, `ppp-sharepoint`, `ppp-power-bi`, `ppp-copilot-studio`;
  - `ppp-app-walk`: walks through your running app in Edge with automated clicks, reviews layout and usability from measurements and pictures, checks expected values and load times, reproduces errors, compares with the last run, and builds the illustrated Word handbook from its Markdown text, and training videos;
  - `ppp-sessions`: on your request, uploads the session logs of your ppp projects to a private repository of yours, to improve ppp from them;
  - `ppp-setup`: checks what ppp needs on this computer (Python, git, pac, Playwright with Edge and ffmpeg, python-docx, Word, the packages of bi-design) and, after your yes, installs the missing Python packages (`ppp setup --check`, `ppp setup --install`).
- **Command line `ppp`** (Python standard library only; `ppp --help` lists every command with its options):

  | Task | Commands |
  |---|---|
  | Solution offline | `unpack`, `inventory`, `verify` (checks C1–C14), `pack` |
  | Connected project | `connect`, `export`, `import`, `tenant`, `members`, `runs` |
  | Checks per module | `canvas` (screen YAML before "paste code"), `pbi` (Power BI as PBIP: `list`, `check`), `schema` (SharePoint lists), `formulas` (App.Formulas to de-DE) |
  | Generators and tests | `run` (project scripts with the central building blocks and the flow simulator `wdl_sim`), `setupflow` |
  | Project files | `init`, `new`, `check`, `migrate`, `archive`, `tidy`, `mail` (read an Outlook `.msg`) |
  | Storage | `storage`, `backup`, `restore` |
  | Across projects | `projects` (register of this computer), `catalog` (building blocks that proved themselves), `team` (shared team folder) |
  | Documents | `walk` (app walk in Edge), `guide` (Word handbook, quick guide, exercise sheet, training deck) |
  | Computer | `setup`, `settings`, `usage`, `sessions` |

- **Hooks** for session start, turn end and compaction; they run only in ppp projects and never block. One more refuses a direct call of `pac` in a connected project, so that the tenant is reached through `ppp` and its checks only.

## The optional plugins
ppp never assumes that one of them is enabled. Before it relies on one, the agent checks whether its skill is in the skill list of the session, and asks you on a card if it is not.

### bi-design: the corporate design
[bi-design/README.md](bi-design/README.md)
- **Skill `bi-designer`**: the brand for everything visual: colours as tokens with roles and allowed contrast pairs, fonts, logo and icon rules, and recipes for Power Apps, Power BI, PowerPoint, Word, Excel, charts, web, HTML mail and Teams cards.
- **Agent and skill `bi-ppt`**, generator **`bippt`**: PowerPoint decks in the BI master, built from a specification, with slides copied from the BI Slide Library; new versions of existing decks, conversion of foreign decks, brand check and render for review. Skill `bi-inhalt` works out the content of a deck in a dialogue first.
- **What ppp takes from it**: the theme of a canvas app, the look of a click prototype, the theme of a Power BI report, the Word template of the handbook, and the training deck per role (`ppp guide --kind deck` calls `bippt`).
- Until 2.13.0 bi-design had a repository of its own (`portolasas/bi-design`, now archived). If you installed it from there, see "Moving from the former bi-design repository" below.

### bi-deneb: custom visuals for Power BI
[bi-deneb/README.md](bi-deneb/README.md)
- Builds a Deneb visual (Vega-Lite or Vega) from a brief: 17 types such as bullet, dumbbell, waterfall, timeline, box plot, and `custom` for a hand-written specification.
- Renders it locally with invented rows in three sizes, checks fields, Deneb rules, brand colours, contrast and overlapping text, and embeds it into the report (PBIR). It reads metadata of the model only, never row data.
- The local render proves the picture, not the data: a visual counts as done when you have opened it in Power BI Desktop.

### Power BI reports: brand design and standard visuals first
Two rules of the skill `ppp-power-bi` hold with or without the optional plugins:
1. **Every report is built in the brand design.** It carries the brand theme of `bi-designer`; `ppp pbi check` reports a report without a custom theme (R10). Without bi-design the agent asks before a page is designed; a neutral look is your decision, never the silent default.
2. **Standard visuals first.** A page is built from the standard visuals of Power BI. A custom visual (Deneb) stands only where a named requirement cannot be met by a standard visual; the README of the module records the requirement, and `ppp pbi check` names the Deneb visuals of a report (R11).

## Requirements
- VS Code with GitHub Copilot and agent plugins enabled, or Claude Code.
- Python 3.10 or newer. On Windows simplest with `python` on `PATH` (installer option "Add python.exe to PATH"); `python --version` in a new terminal shows it. A Python outside `PATH`, such as a conda, mamba or miniforge environment, works too: run `ppp setup` once with it (`<path to python.exe> -I <plugin>\tools\ppp.py setup`); the VS Code hooks and the tool call then take it from `~/.ppp/python.txt` (the Claude Code hooks still start `python3` or `python` from `PATH`). The VS Code hooks never block a tool call when no Python starts.
- Power Platform CLI `pac` (in `PATH`, from the VS Code extension Power Platform Tools, or in `~/.dotnet/tools`). A connected project also needs pac signed in on the computer (`pac auth create`, once, by you).
- git. Each project chooses its storage at intake: a private GitHub repository, or a local folder without any server (git without a remote, backed up on request with `ppp backup` into a folder you choose, restored with `ppp restore`). Bitbucket is prepared.
- In VS Code a model that follows the agent text: GPT-6.1 Sol for building, Claude Opus 5.5 for clarification, planning and diagnosis. Not GPT-6 Luna. GPT models with the small context size (272k) in the model picker: the long context costs double above 272k; Claude models cost the same in both.

Optional, only for the feature named:

| Package or program | For |
|---|---|
| `playwright` and an installed Microsoft Edge | `ppp walk` (app walk); `ppp walk --video` uses the ffmpeg of playwright |
| `python-docx` | `ppp guide` (Word handbook, quick guide, exercise sheet) |
| Microsoft Word | `ppp guide --word` (update table of contents and fields) |
| plugin bi-design with its packages (`bippt einrichten`: python-pptx and others, `pip --user`) | `ppp guide --kind deck`, agent `bi-ppt` |
| PowerPoint | render of a deck for review (bi-design) |
| `vl-convert-python`, Pillow (`bideneb setup`, `pip --user`) | local render of bi-deneb; without them only its static rules run |
| Power BI Desktop | opening a report (PBIP) and proving a visual |

ppp itself is called with `python -I`; `bippt` and `bideneb` without `-I`, because it hides the packages of `pip --user`.

## Quick start

### 1. Install
**VS Code.** Four steps, no JSON editing. Python 3.10 or newer and git must be on the computer (see Requirements).
1. **Install VS Code** and sign in to GitHub Copilot (account icon at the bottom left).
2. **Install ppp and add the marketplace.** Paste this link into the address bar of your browser, let it open VS Code and confirm there:
   ```
   vscode://chat-plugin/install?source=portolasas/ppp-plugin&plugin=ppp
   ```
   It installs ppp and adds the marketplace `portolasas/ppp-plugin`. The Agents view › Customizations › Browse then shows every plugin of this marketplace: install **bi-design** and **bi-deneb** there if you want them. Plugins added to the marketplace later show up there too. The marketplace alone, without installing anything: `vscode://chat-plugin/add-marketplace?ref=portolasas/ppp-plugin`.
3. Run "Developer: Reload Window" and choose the agent **ppp** once in the agent picker of the Agents view; it stays chosen. With the optional plugins the picker also shows `bi-ppt` and `bi-deneb`; in a ppp project you stay with `ppp`, which loads their skills itself.
4. **Say "check ppp".** The skill `ppp-setup` checks what ppp needs and asks on one card. It installs the missing Python packages (Playwright with its ffmpeg, python-docx, the packages of bi-design) and sets up VS Code (`ppp setup --vscode`): GPT-6.1 Sol with thinking level high and the context of 272K for new sessions of the Agents view, the extensions Power Platform Tools (with `pac`), Python with Python Environments, Pylance and Python Debugger and PowerShell, a few settings for git, diffs and the model of the chat, Allow All as the starting approval of new agent sessions (tool calls run without asking; the hooks of ppp still refuse a direct pac call), and a model list with only GPT-6.1 Sol, Claude Opus 5.5, Claude Sonnet 5.5, Claude Haiku 5.5 and GPT-6 Astra, Sol and Opus pinned (written into the database of VS Code once every window of it is closed). Each file is backed up first; values you chose yourself stay. Where a group policy blocks the command line of VS Code, it prints one link per extension instead: paste each into the address bar of the browser and click Install in VS Code (`vscode:extension/microsoft-isvexptools.powerplatform-vscode` `vscode:extension/ms-python.python` `vscode:extension/ms-python.vscode-python-envs` `vscode:extension/ms-python.vscode-pylance` `vscode:extension/ms-python.debugpy` `vscode:extension/ms-vscode.powershell`).
5. **Restart, enable, sign in, new chat.** On the first setup the extensions are only installed, so pac is not found yet:
   - close every window of VS Code and open it again;
   - Agents view › Customizations › Extensions: enable each extension ppp installed for the Agents view (Power Platform Tools, Python, Python Environments, Pylance, Python Debugger, PowerShell); an installed extension stays off in the Agents view until you enable it there;
   - when Power Platform Tools asks, sign in with your Microsoft work account: without it pac finds no environments and no solutions;
   - start a **new chat** in the Agents view and say "check ppp" again there, not in the chat of the first setup.

**Optional: the profile.** `ppp setup --vscode` sets all of it up without a profile. The profile [`setup/ppp.code-profile`](https://raw.githubusercontent.com/portolasas/ppp-plugin/main/setup/ppp.code-profile) (right-click › "Save link as...", keep the extension `.code-profile`; Command Palette › "Profiles: Import Profile..." › "Select File...", keep everything ticked, "Use for New Windows", "Create") carries the same extensions and settings into a profile of its own for the normal window.

By hand instead of the links: open the Settings, search for `chat.plugins.marketplaces`, choose "Add Item" and enter `portolasas/ppp-plugin` (or Agents view: Customizations › Browse › Configure Marketplaces › Add Marketplace); install the plugins from Customizations › Browse and confirm the trust prompt. If ppp does not appear, check that agent plugins are on (`chat.plugins.enabled`; a policy of your company may switch them off).

**Claude Code.** Once per computer:
```
/plugin marketplace add portolasas/ppp-plugin
/plugin install ppp@ppp
```
Optional:
```
/plugin install bi-design@ppp
/plugin install bi-deneb@ppp
```
Then start a new session.

**Moving from the former bi-design repository.** If bi-design is installed from `portolasas/bi-design` (up to 2.13.0), remove that installation once, otherwise the agent `bi-ppt` and the skills appear twice and the old copy gets no new versions. VS Code: uninstall that plugin and delete `portolasas/bi-design` from `chat.plugins.marketplaces`. Claude Code: `/plugin uninstall bi-design@bi-design`, then `/plugin marketplace remove bi-design`. Then install bi-design from this marketplace. Your settings in `~/.bi-design/config.json` stay.

`ppp setup` prints these entries for your computer and removes an agent copy of ppp versions before 0.2.0.

### 2. Start a project
Open a folder for the project and tell the agent what you want, for example:
- "New solution: an app to request training slots, with an approval flow."
- "Take over the existing solution; the export is in `exchange/`."

The agent asks name, prefix, modules, mode (small, medium, large), storage and handbook language on one card and creates the project with `ppp init`. For an existing solution it unpacks the export, inventories every flow and drafts the specs.

### 3. Work in packages
1. **Clarify** the requirements in card rounds (`specs/`, `decisions/`), optionally with a click prototype. The agent looks into the catalog of building blocks that proved themselves in your other projects.
2. **Plan** packages in `ROADMAP.md`.
3. **Build** each package in `changes/NNN-name/`: you confirm the proposal, the agent builds and checks offline, packs the solution into `exchange/`, you import it (or the agent does, in a connected project) and test the critical scenarios on cards. App screens reach Power Apps Studio by "paste code".
4. **Document**: an app walk in Edge takes the pictures, and `ppp guide` builds handbook, quick guide and exercise sheet per role in Word from one Markdown text, and with bi-design a training deck per role.
5. **Go live**: full test, move to test and production, hypercare.

After a break the agent continues from `STATE.md`.

### 4. Updates
VS Code fetches new versions itself (with `extensions.autoUpdate`, about every 24 hours); reload the window afterwards. In Claude Code, for each plugin you installed:
```
/plugin marketplace update ppp
/plugin uninstall ppp@ppp
/plugin install ppp@ppp
```
What changed is in [CHANGELOG.md](CHANGELOG.md); the optional plugins list their own changes in [bi-design/CHANGELOG.md](bi-design/CHANGELOG.md) and [bi-deneb/CHANGELOG.md](bi-deneb/CHANGELOG.md).

## Project layout
```
project.json          name, prefix, modules, mode, storage, solutions
STATE.md              where the work stands; read first in every session
AGENTS.md             project rules for the agent
ROADMAP.md            all packages with goal and status
specs/, decisions/    confirmed requirements and decisions
changes/NNN-name/     one folder per package (proposal, tasks); finished ones in changes/archive/
solution/<Name>/      working copy of the solution (pac unpack format)
components/<module>/  inventory, screens, list schema, flow documents, generators, the report as PBIP
environments/         connected projects: address, role and use of each environment
exchange/             exports in, packages out (in git only with exchange git in project.json)
inputs/, docs/, ...   material as handed over; handbook and training; created when needed
```

## Across projects
- `ppp projects` lists the ppp projects of this computer.
- `ppp catalog` lists the building blocks that proved themselves in your other projects; only you call something proven, on a card.
- `ppp team share` shares a project with a team folder you set (`ppp settings --team <folder> --person <name>`): who works on it and what proved itself; a local project then backs up there.

## Data
ppp keeps everything in your project folder and its git repository. Exports can contain personal data and tenant details; keep project repositories private, or choose the local folder, which stores no project data on GitHub. Backups of a local project go only to the folder you set (`ppp settings --backup <folder>`). In Power BI projects the agent reads metadata only: no row data, no exports of data, no `.pbi/cache.abf`. Session logs leave the computer only when you ask for an upload, only to the repository you name (`ppp settings --sessions <clone>`), and only for projects on GitHub; keep it private.

The plugins hold no tenant, personal or customer data. bi-design and bi-deneb contain brand material of Boehringer Ingelheim (colours, the PowerPoint and Word templates with their embedded fonts, the slide library); it is not under the licences named in THIRD_PARTY.md.

## What is not proven yet
- Installing bi-design and bi-deneb from this marketplace was not yet tried in VS Code and Claude Code; they lie in subfolders of the repository (`./bi-design`, `./bi-deneb`).
- No visual generated by `bideneb` has been opened in Power BI Desktop so far.

## More
- [CHANGELOG.md](CHANGELOG.md): versions and changes.
- [THIRD_PARTY.md](THIRD_PARTY.md): adopted templates, their licences, and the icon.
- [bi-design/README.md](bi-design/README.md), [bi-deneb/README.md](bi-deneb/README.md): the optional plugins.
