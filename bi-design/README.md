# bi-design

Plugin für **VS Code (GitHub Copilot)** und **Claude Code**, das Agenten das Corporate Design von Boehringer Ingelheim beibringt. Es ist ein wählbares Plugin im Marktplatz von ppp (`portolasas/ppp-plugin`), neben ppp und bi-deneb, und trägt die Version von ppp.

Verbindlich ist der **BI-Master v2.1** (How-to slides): nur seine Designfarben und Custom Colors, keine Abstufungen, keine Standardfarben, Fußzeile mit Vertraulichkeitsvermerk. Referenzdecks liefern Storyline und Textmuster, nicht die Farben.

- **Skill `bi-designer`** – Marke für alles Visuelle: Farben (Tokens, Rollen, erlaubte Kontrastpaare), Schriften, Logo- und Symbolvarianten, 895 Icons, Rezepte für Power Apps, Power BI, PowerPoint/Word/Excel, Diagramme, Web, HTML-Mail, Teams-Karten. ppp nutzt ihn für Power-Apps-Theme, Prototypen und Power-BI-Theme.
- **Agent und Skill `bi-ppt`** – PowerPoint im BI-Master v2.1: aus Transkripten, Projektaufträgen, Notizen oder Excel ein neues Deck bauen, eine neue Version eines bestehenden Decks erzeugen (z. B. Projektteam-Update → Steering-Update), fremde Decks ins BI-Design umwandeln, Brand-Regeln prüfen und zur Sichtprüfung rendern.
- **Skill `bi-inhalt`** – arbeitet den Inhalt im Dialog aus (Ziel, Kernbotschaft, Storyline, Inhalt und Bildform je Folie) und übergibt ein abgenommenes Briefing an bi-ppt.
- **Generator `bippt`** (Python, python-pptx) – baut die Folien aus einer Spezifikation (JSON) mit Folientypen wie Status, Vergleich, Prozess, Timeline/Gantt, Maßnahmen, Kennzahlen, Diagramm, Tabelle – und kopiert gestaltete Folien aus der offiziellen **BI Slide Library** (184 Folien) ins Deck und füllt sie (`{"bib": n, …}`, `bippt katalog`). Änderungen später = Spec ändern und neu bauen; bestehende Folien ändert `aendern` (Bild tauschen, Absätze, Läufe, Formen verschieben). Zu jedem Deck schreibt `bippt bauen` die Folienbeschreibung `<Name>.md` mit Baustand je Folie.

## Voraussetzungen
- VS Code mit GitHub Copilot und Agent Plugins, oder Claude Code.
- Python 3.9 oder neuer, aufgerufen wie bei ppp (Windows `python`, Mac `python3`), aber ohne `-I`, weil `-I` die mit
  `pip --user` installierten Pakete ausblendet. Die Pakete installiert `bippt einrichten` mit `pip --user`, ohne venv.
- PowerPoint zum Rendern (Mac oder Windows); sonst nur Prüfen.
- Für Logos und Icons der Ordner BrandDesign (nicht im Repo; Schriftdateien sind lizenziert).

## Kurzanleitung

### 1. Installieren
bi-design kommt aus dem Marktplatz von ppp. Es wird nicht mit ppp installiert: Jeder wählt es selbst.

**VS Code.** Ohne JSON und ohne Installationsskript. Den Marktplatz eintragen, falls er für ppp noch nicht eingetragen
ist: Einstellungen öffnen, nach `chat.plugins.marketplaces` suchen, „Element hinzufügen“ und `portolasas/ppp-plugin`
eingeben, oder in der Agents-Ansicht: Customizations › Browse › Configure Marketplaces › Add Marketplace. Dann
**bi-design** aus dem Marktplatz installieren (Customizations › Browse oder Erweiterungen-Ansicht unter Agent Plugins)
und die Vertrauensabfrage bestätigen. Danach „Developer: Reload Window“.

Erscheint das Plugin nicht, prüfen, ob Agent Plugins eingeschaltet sind (`chat.plugins.enabled`).

**Claude Code.** Einmal je Rechner:
```
/plugin marketplace add portolasas/ppp-plugin
/plugin install bi-design@ppp
```
Danach eine neue Sitzung.

**Umstieg von `portolasas/bi-design` (bis 2.13.0).** Die alte Installation entfernen, sonst stehen Agent und Skills
doppelt da: in VS Code das Plugin bi-design aus der alten Quelle deinstallieren und den Marktplatz
`portolasas/bi-design` aus `chat.plugins.marketplaces` löschen; in Claude Code `/plugin uninstall bi-design@bi-design`
und `/plugin marketplace remove bi-design`. Die Einstellungen in `~/.bi-design/config.json` bleiben.

### 2. Einrichten (einmal je Rechner)
Im Agenten-Menü **bi-ppt** wählen (Claude Code: Skill `/bi-design:bi-ppt`) und schreiben: „Prüfe die Umgebung.“ Der Agent ruft `bippt umgebung` auf und fragt per Karte, bevor er
- fehlende Python-Pakete installiert (`bippt einrichten`),
- alte Kopien von BI-PPT 1.x oder PPP 0.17 aus `~/.copilot`, `~/.claude` und `~/.bi-ppt` löscht (`bippt aufraeumen --ja`); sie verdecken Agent und Skills des Plugins,
- den Ordner BrandDesign einträgt (`bippt konfig --setze asset_root=<Ordner>`).

Erwartet: `ERGEBNIS: OK`. Auf dem Mac fragt PowerPoint beim ersten Rendern nach Dateizugriff: „Auswählen…“ › Ordner `Dokumente/BI-PPT-Render` › „Zugriff erteilen“.

### 3. Eine Präsentation bauen
Mit dem Agenten **bi-ppt**, zum Beispiel:
- „Baue aus `Transkript.vtt` und `Projektauftrag.docx` ein Steering-Committee-Update für den 12.11.“
- „Mach aus `Team-Update_KW44.pptx` die Fassung für das Steering Committee.“
- „Bring `Lieferantenpraesentation.pptx` ins BI-Design.“
- „Prüfe `Entwurf.pptx` gegen die Brand-Regeln.“

Der Agent liest die Quellen, stellt eine gebündelte Rückfragerunde (Publikum, Datum, Ampeln, Widersprüche), schreibt `<Name>.spec.json` neben die Ausgabe, baut, prüft und rendert. Neben der PPTX liegen danach die Spec und die **Folienbeschreibung** `<Name>.md`: je Folie Typ, Gestaltung, Kernaussage, Inhalt und Notizen, damit andere Agenten und Sitzungen das Deck lesen können, ohne die PPTX auszulesen. Eine vorhandene Vorlage (z. B. von ppp) wird über `dokument` in der Spec zur Folienbeschreibung; ihr Text bleibt, bippt hängt seinen Abschnitt an.

Liegt der Arbeitsordner in einem Git-Repo (z. B. ein ppp-Projekt), committet der Agent wie ppp nach jedem abgeschlossenen Schritt ohne Rückfrage und pusht nach `main`: PPTX, Spec, Folienbeschreibung und neue Bilder.

Spätere Änderungen („Ändere auf Folie 4 den Termin“) liest der Agent aus der Folienbeschreibung und ändert nur die betroffenen Folien; `bippt bauen` meldet in `ÄNDERUNGEN`, welche Folien sich geändert haben. Wurde das Deck nach dem Bau in PowerPoint bearbeitet, bricht `bippt bauen` ab, statt die Handänderungen zu überschreiben; der Agent übernimmt das Deck dann als Basis und ändert nur die betroffenen Folien.

Für andere Medien (Word, Excel, Diagramme, Power BI, Web, Mail) genügt im normalen Chat „im BI-Design“; dann lädt der Agent den Skill `bi-designer`.

### 4. Aktualisieren
VS Code holt neue Versionen selbst (bei `extensions.autoUpdate` etwa alle 24 Stunden), danach „Developer: Reload Window“. Claude Code:
```
/plugin marketplace update ppp
/plugin uninstall bi-design@ppp
/plugin install bi-design@ppp
```
Was sich geändert hat: [CHANGELOG.md](CHANGELOG.md).

## Aufbau
| Pfad | Inhalt |
|---|---|
| `plugin.json`, `.claude-plugin/plugin.json` | Manifeste für VS Code bzw. Claude Code (Aufbau A wie ppp). Der Marktplatz von ppp nennt das Plugin mit der Quelle `./bi-design` |
| `com.github.copilot/agents/bi-ppt.agent.md` | Agent für VS Code |
| `agents/bi-ppt.md` | Subagent für Claude Code |
| `skills/bi-designer/` | Markenregeln (`marken/<profil>/MARKE.md`, `tokens.json`, `icons.txt`), Rezepte je Medium |
| `skills/bi-inhalt/` | Inhalt im Dialog, Briefing |
| `skills/bi-ppt/` | Arbeitsweise, Rückfragen, Folientypen, Umwandeln, Beispiel-Spec |
| `tools/` | Generator `bippt` und `requirements.txt` |
| `vorlagen/BI_Vorlage_16x9.pptx` | Arbeitsvorlage aus dem BI-Master v2.1 (ohne Folien, ohne doppelte Layouts) |
| `vorlagen/BI_Slide_Library.pptx` | offizielle BI Slide Library 3.3 (September 2026), Quelle der Bibliotheksfolien; Übersicht in `skills/bi-ppt/reference/bibliothek.md` |
| `vorlagen/BI_Vorlage_Handbuch.docx` | Word-Vorlage für Handbücher (`bippt wordvorlage`) |
| `vorlagen/How-to slides.pptx` | Original des BI-Masters, Quelle für `bippt vorlage`; wird seit 2.13.0 mitinstalliert (1,4 MB) |
| Repo `portolasas/Agents`, Ordner `bi-ppt` | Agent bi-ppt für den Microsoft 365 Copilot Agent Builder; sein Bauskript packt Generator, Vorlage und Marke aus diesem Plugin in Skill-Pakete |

Einstellungen je Rechner: `~/.bi-design/config.json` (`asset_root`, `vorlage`, `vertraulichkeit`, `marke`, `render_dir`).

## Entwickeln
- Entwickelt wird im Repo von ppp, Ordner `plugin/bi-design/`. Tests dort: `python3 tests/bidesign/run.py` (ohne `-I`, Python mit den Paketen aus `tools/requirements.txt`).
- Die Version ist die von ppp (`tools/version.py bump` im Repo von ppp erhöht sie in beiden Manifesten mit); was bi-design ändert, bekommt einen Eintrag in `CHANGELOG.md`.
- Neuer Folientyp: `tools/bippt/folien.py` (`@folientyp`), Doku in `skills/bi-ppt/reference/folientypen.md`, Beispiel in `skills/bi-ppt/beispiele/beispiel.spec.json`.
- Folienbeschreibung und Baustand: `tools/bippt/beschreiben.py`. Neuer Folientyp: auch Inhalt (`INHALT`) und
  Gestaltung (`_art`) dort ergänzen.
- Textmaße: `text_breite` und `umbrechen` in `tools/bippt/bausteine.py` (Zeichenbreiten von Boehringer Forward,
  Umbruch wie PowerPoint); `text(…, breite=w)` meldet zu breite Wörter, `vorlage.titel_pruefen` zu lange Titel.
- Formen einer Folie immer über `formen.alle()` durchgehen (`tools/bippt/formen.py`): Fremde Decks enthalten Formen,
  bei denen python-pptx abbricht. Änderungen an bestehenden Folien gehören nach `tools/bippt/aendern.py`.
- Neue Marke: Profil in `skills/bi-designer/marken/<profil>/` und eigene Vorlage (`bippt vorlage <deck> -o …`).
- Das Plugin ist das ganze Repo: Was eingecheckt ist, landet auf jedem Rechner, der bi-design installiert.
- Keine Projekt- oder Personendaten und keine Schriftdateien ins Repo. Referenz-Präsentationen und Chats zum Anlernen liegen lokal außerhalb von Git.
