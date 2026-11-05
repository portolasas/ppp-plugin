# Changelog

Versions of the ppp plugin, newest first. Every published change raises at least the patch version and names here what changed; a learning session adds the lesson IDs as evidence (archive `knowledge/lessons/` in the ppp repository).

## 0.16.1 (2026-11-05)
- ppp canvas meldet einzeilige Werte mit ': ' oder ' #' (YAML lehnt sie ab oder schneidet sie ab; Block |-) und warnt vor Filter(<Liste>, … in …) und Search(<Liste>, …) als nicht delegierbar (gefunden beim Bau von ppp-bench S6)

## 0.16.0 (2026-11-05)
- ppp walk nennt jeden Befund einmal beim ersten Bild mit der Zahl weiterer Bilder; report.json behält alle
- ppp walk --check warnt vor key Home/End; Dropdown mit gezählten Pfeiltasten, Scroll-Ziel sichtbar (PAPPS-20261105-WIN-01)
- ppp-app-walk: Werte und leere Zustände gehören zum Review
- ppp canvas warnt vor Sum(/Average( mit & ohne Coalesce; ppp-power-apps: Sum einer leeren Tabelle ist Blank (PAPPS-20261105-MAC-01)
- ppp-app-walk §6 verweist auf GEN-20261104-MAC-01

## 0.15.1 (2026-11-05)
- Modellempfehlung nennt bei GPT-Modellen die kleine Kontextgröße (272k): der große Kontext kostet ab 272k das Doppelte; Claude-Modelle kosten in beiden gleich (ARBEITSWEISE A-9)

## 0.15.0 (2026-11-05)
- ppp guide --kind deck: Schulungsdeck je Rolle in PowerPoint im Corporate Design (bippt aus bi-design) aus demselben Handbuch-Markdown und denselben Bildern wie Word; eine Folie je Aufgabe mit Walk-Bild, Kurzanleitung als Kapitel, Übungen mit ausgeblendeten Lösungen, Schritttexte und Hilfelisten in den Sprechernotizen; Zeilen <!-- deck: skip|title|heads|icons|steps|tiles|ampel|shot --> steuern Abschnitte, Word ignoriert sie; --bippt, ohne bi-design nur die Spec
- project.json: optional trainingFormat word|powerpoint|both; ppp-docs fragt es vor den Dokumenten für Nutzer ab (Nutzer 05.11.2026: bei powerpoint bleibt das Handbuch Word, Kurzanleitung und Übungen kommen ins Deck)
- ppp-docs: ein Deck lehrt, was das Werkzeug braucht, nicht Fachwissen der Nutzer (z. B. Schichtzeiten mit deck: skip); was Nutzer im Werkzeug beurteilen müssen, etwa wie sicher eine Prognose ist, bekommt einen eigenen Abschnitt

## 0.14.0 (2026-11-04)
- ppp guide --word: Word aktualisiert Inhaltsverzeichnis und Felder und speichert (macOS über Launch Services, Windows über COM, dort noch nicht erprobt); --orientation portrait|landscape
- ppp guide: Absatz zwischen zwei Tabellen (Word verschmolz sie), kurze Tabellen auf einer Seite, Spaltenbreiten nach Inhalt, Legende in einer Zeile, Bilder höchstens halbe Seitenhöhe, Einleitungszeilen wie 'Wenn etwas nicht klappt:' bei ihrer Liste, jede Übung auf einer Seite, Kapitelüberschrift von Kurzanleitung und Übungsblatt entfällt

## 0.13.1 (2026-11-04)
- ppp guide: wiederholte Klicks auf dasselbe Steuerelement zählen als eine Handlung; Tabellen zählen für die Prüfung auf Entwicklersprache und die Länge der Kurzanleitung

## 0.13.0 (2026-11-04)
- ppp guide: ein Handbuch in Markdown ergibt Handbuch je Rolle (--role, <!-- for: … -->), Kurzanleitung und Übungsblatt je Rolle (--kind quick|exercises, <!-- kind: … -->, Lösungen am Ende nach <!-- solution -->); Überschriften ohne Inhalt für die Rolle entfallen
- ppp guide: Schritt, Bild, Beschriftung und Legende auf einer Seite, Bilder höchstens 60 % der Seitenhöhe, hängender Einzug der Schritte, Legende abgesetzt, Kasten für '> …', Ankreuzfeld für '- [ ] …', <!-- pagebreak -->, Tabellenkopf wiederholt
- ppp guide warnt bei mehr als drei Klicks ohne Text in einem Walk, bei Wörtern aus <!-- avoid: … --> und bei einer Kurzanleitung über etwa einer Seite; Hinweis bei einem Walk einer anderen Rolle
- ppp-docs: Raster je Aufgabe (Wozu, Schritte, Ergebnis, Wenn etwas nicht klappt), Schreibregeln ohne Entwicklersprache, technische Notizen in docs/handbook/README.md, Kurzanleitung und Übungsblatt je Rolle, Durchsicht je Rolle (aus einer Recherche zu DITA-Profiling, Job Aids und dem Microsoft Writing Style Guide)

## 0.12.0 (2026-11-04)
- ppp walk startet sofort und wartet nur auf einer Anmeldeseite bis zu zehn Minuten (--signin), jeder Schritt höchstens --timeout; Live-Zeilen für Fenster, App bereit und jeden Schritt; Fenster vorn
- ppp walk: type stoppt sofort an einem schreibgeschützten Feld, --check meldet type auf einen DatePicker; Datum über click, key und expect (PAPPS-20261103-WIN-07)
- ppp walk: der Mauszeiger verlässt die App vor jedem Bild, außer nach hover (PAPPS-20261104-WIN-01)
- ppp guide: Dokumenttitel als Eigenschaft und TITLE-Feld statt STYLEREF "Title" in Kopf- und Fußzeile (GEN-20261104-WIN-02)
- ppp new lesson: überspringt auch IDs, die Commit-Nachrichten zu lessons/ als archiviert nennen
- ppp-app-walk: Testbeispiele für Handbücher mit echten Stammdaten, Anlage und Bereinigung per schreibendem Walk
- ppp-docs: Fehlverhalten aus einem Handbuch-Walk auf eine Entscheidungskarte vor dem Kapiteltext
- Agent: Startprompt eines neuen Chats im Chat über der Haltepunkt-Karte; Fehlgriff-Zeile für git diff --check mit CRLF (GEN-20261104-WIN-01)

## 0.11.1 (2026-11-03)
- ppp-app-walk: a project copies the Word template bi-designer names (bi-design 2.12.0) instead of building its own

## 0.11.0 (2026-11-03)
- ppp-docs: the clicks of a chapter come from its walk alone, the text holds purpose, prerequisites, result and help; ppp guide warns about numbered steps beside a walk line
- ppp walk records the screens its pictures show; ppp check names handbook walks whose screens changed since; ppp-package and tasks.md close a package with a current handbook
- ppp-docs: the handbook names its version, date and solution version and has a section "New in this version"
- ppp-clarify: an accepted decision stays as written, a new one supersedes it

## 0.10.0 (2026-11-03)
- ppp walk: pictures show the app's frame only, without the player's name and photo (PAPPS-20261103-WIN-05)
- ppp walk: frames on the visible part of each marked control, minimal scrolling in the app's containers; less than 97 % visible stops the walk in the first viewport, a hint in further ones; text selections cleared before each picture; type fills the control's input and checks its value (PAPPS-20261103-WIN-06)
- ppp walk: overviews of up to six pictures per viewport in exchange/walks/<name>/sheets/; ppp-app-walk looks at them instead of every single picture, a guide's walk has one viewport
- ppp guide: builds the Word handbook from docs/handbook/<name>.md; <!-- walk: <name> --> inserts a walk's steps and pictures, <!-- toc --> a table of contents; ppp-docs keeps the whole handbook text in that Markdown
- ppp-app-walk: every run goes through ppp walk, a missing feature becomes a lesson proposal before a project script; one chat per role of a guide; Word template once from bi-designer's recipe, markColor from its tokens
- ppp new lesson: skips IDs still in the git history of lessons/, so an ID a learning session removed is not given out again
- ppp usage: tokens of a Copilot session without a shutdown event come from its usage records

## 0.9.0 (2026-11-03)
- ppp-app-walk: after a fix round only the walks of the changed screens run again; findings left go on a decision card before another round

## 0.8.0 (2026-11-03)
- ppp walk: L3 measures text rectangles against clipping boxes inside the control (dropdown chevron, combo box frame); new finding L8, a word broken over two lines (PAPPS-20261103-WIN-02, PAPPS-20261103-WIN-03)
- ppp-app-walk: after a publication the user confirms the update or connection bar first; the first step expects a control of the new build (PAPPS-20261103-WIN-04)
- layout.md: a classic dropdown's chevron and padding take about 54 px (PAPPS-20261103-WIN-02)
- ppp-package: a package of screens only skips ppp tidy, whose message says so (GEN-20261103-WIN-01); the transfer solution may keep members the user wants, unchanged from its latest export
- expressions.md: reading the answer of Edit app role assignment (PA-20261103-WIN-01)
- Agent: misfire line for the optional design.md of a package

## 0.7.0 (2026-11-03)
- ppp walk --check: Patch, Remove, RemoveIf, Update and UpdateIf on a collection filled by Collect or ClearCollect are no write (PAPPS-20261102-WIN-02)
- ppp walk: findings L6 (button label on more than one line) and L7 (painted border cut by a parent); a layout review opens every dropdown, combo box and date picker (PAPPS-20261103-WIN-01)
- ppp-app-walk: scroll targets a control outside nested galleries (PAPPS-20261102-WIN-01); keys leave a classic dropdown unchanged, expect the shown value (PAPPS-20261102-WIN-02); a review with unfixed findings ends with a decision card
- ppp-power-apps layout: classic button borders lie 0.5 px outside the button, leave 2 px; size labels with the real font (PAPPS-20261103-WIN-01)
- ppp-package: one card for all screens of a package; ppp new package skips numbers already in ROADMAP.md (GEN-20261102-WIN-01)
- ppp-sessions: the user's call is the permission to upload; GPT-6.1 Sol instead of GPT-6 Luna

## 0.6.0 (2026-11-02)
- Version 0.6.0 gathers the walk tools since 0.5.1: --diagnose, comparison with the last run, load times, usability findings, roles with per-role guides, --video and mock-ups by project path (PLUGIN PL-21).

## 0.5.7 (2026-11-02)
- ppp walk --video records a walk with captions, click ring and masks in every frame to exchange/walks/<name>/video/; ppp walk reports a browser that does not start in one line (user, 2026-11-02).

## 0.5.6 (2026-11-02)
- Roles: a walk with role {name, identity} runs in its own browser profile and stops without a picture unless the app shows that identity; a click on a disabled control stops the run; ppp guide --role builds one guide per role and refuses pictures not proven as that role; failure pictures stay in exchange/ (user, 2026-11-02).

## 0.5.5 (2026-11-02)
- ppp walk: usability findings A1 clickable without label, A2 click area under 24 px, A3 text contrast under 4.5:1; fix: a first run without pictures broke the next run (user, 2026-11-02).

## 0.5.4 (2026-11-02)
- ppp walk measures start and action times with their requests and warns when a step is clearly slower than in the last complete run (user, 2026-11-02).

## 0.5.3 (2026-11-02)
- ppp walk compares every picture with the last complete run and names changed pictures with area and a diff in exchange/walks/<name>/diff/ (user, 2026-11-02).

## 0.5.2 (2026-11-02)
- ppp walk --diagnose records every error of the app per step, with the bodies of failed responses, in exchange/walks/<name>/diagnosis.json; ppp-diagnose reproduces with it before asking (user, 2026-11-02).

## 0.5.1 (2026-11-02)
- ppp walk: step expect checks what a control shows (equals, contains, count, absent, within); a deviation is reported with a picture and the walk goes on. ppp-package: the user tests the critical scenarios no walk covers (ARBEITSWEISE A-5, user, 2026-11-02).

## 0.5.0 (2026-11-02)
- Skill ppp-app-walk with ppp walk and ppp guide (PLUGIN PL-21, user, 2026-11-02): the agent walks through a running canvas app in Edge with Playwright (clicks, typing, wait for content), takes pictures with numbered frames and masks as a browser overlay, reports measured layout findings and console and HTTP errors, and builds an illustrated Word guide with python-docx. Writing steps need identifiable, removable test data and a card, in any environment. Clicks in the tenant are still to be proven.

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
