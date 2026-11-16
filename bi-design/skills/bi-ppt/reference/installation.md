# Installation, Update, Fehlerbilder

Quelle: Plugin **bi-design** aus dem Marktplatz von ppp (`portolasas/ppp-plugin`), wählbar neben ppp. Es bringt Agent `bi-ppt`, die Skills
`bi-ppt` und `bi-designer`, den Generator `bippt` und die Vorlage mit. Einstellungen je Rechner: `~/.bi-design/config.json`.

## Installieren
- **VS Code:** Marktplatz in den Einstellungen eintragen: `chat.plugins.marketplaces` › „Element hinzufügen“ ›
  `portolasas/ppp-plugin` (oder Customizations › Browse › Configure Marketplaces › Add Marketplace); kein JSON nötig.
  **bi-design** aus dem Marktplatz installieren (Customizations › Browse oder Erweiterungen-Ansicht unter Agent
  Plugins); „Developer: Reload Window“; Agent **bi-ppt** im Agenten-Menü wählen. Erscheint es nicht:
  `chat.plugins.enabled` eingeschaltet?
- **Claude Code:** `/plugin marketplace add portolasas/ppp-plugin`, `/plugin install bi-design@ppp`, neue Sitzung.
  Skill `/bi-design:bi-ppt` im Hauptchat oder Subagent `bi-ppt` für abgegrenzte Bauaufträge.
- **Vorher aus `portolasas/bi-design` installiert (bis 2.13.0):** diese Installation entfernen, sonst stehen Agent und
  Skills doppelt da (Claude Code: `/plugin uninstall bi-design@bi-design`, `/plugin marketplace remove bi-design`;
  VS Code: Plugin aus der alten Quelle deinstallieren, Marktplatz `portolasas/bi-design` aus den Einstellungen löschen).
- Dann `bippt umgebung`; Pakete mit `bippt einrichten`, alte Kopien mit `bippt aufraeumen --ja`.

## Python
- Wie bei ppp: Windows `python` (Firmenrechner: Python 3.13), macOS `python3`; nicht `py`. Mindestens Python 3.9.
- Anders als ppp **ohne `-I`**: bippt braucht Pakete aus PyPI, und `-I` blendet die mit `pip --user` installierten aus.
- Pakete nur mit `bippt einrichten` (`"<Interpreter>" -m pip install --user -r requirements.txt`), kein venv:
  Gruppenrichtlinien sperren virtuelle Umgebungen. In einem bereits aktiven venv installiert es ohne `--user` dorthin.
- Mehrere Pythons (auf dem Mac z. B. 3.9 und 3.10): `bippt umgebung` nennt in `Aufruf` den absoluten Pfad des
  Interpreters; denselben für alle Befehle verwenden, sonst fehlen die Pakete.

## Aktualisieren
VS Code holt neue Versionen selbst (bei `extensions.autoUpdate` etwa alle 24 Stunden), danach „Developer: Reload Window“.
Claude Code: `/plugin marketplace update ppp`, dann `/plugin uninstall bi-design@ppp` und
`/plugin install bi-design@ppp`, neue Sitzung.

## `bippt umgebung` meldet …
| Meldung | Abhilfe |
|---|---|
| Paket pptx/lxml FEHLT | `bippt einrichten` (nach Zustimmung). Proxy: `pip config set global.proxy http://<proxy>:<port>`. Kein venv anlegen: Gruppenrichtlinien sperren es oft |
| Python fehlt oder < 3.9 | Windows ohne Adminrechte: `winget install -e --id Python.Python.3.12 --scope user`, neues Terminal |
| ALT … | `bippt aufraeumen --ja` (übernimmt `~/.bi-ppt/config.json`), dann VS Code neu laden bzw. neue Sitzung |
| Vorlage FEHLT | Plugin neu installieren, oder `bippt vorlage <BI-Deck.pptx>` (jedes Deck im BI-Master taugt) |
| Marke … Notstand | Profil fehlt in `skills/bi-designer/marken/`; Farben laufen trotzdem (eingebaut) |
| Icons 0 | `bippt konfig --setze asset_root=<BrandDesign-Ordner>` (Ordner mit Icons_darkgreen/ …) |
| Rendern über nichts | PowerPoint fehlt → nur `pruefen`; optional LibreOffice |

## Rendern – bekannte Fallen
- **Mac, Dialog „Dateizugriff erteilen“:** PowerPoint ist sandboxed. Einmalig „Auswählen…“ → Ordner
  `Dokumente/BI-PPT-Render` (den Ordner, nicht eine Datei) → „Zugriff erteilen“. bippt gibt PowerPoint nie andere Ordner.
- **Mac, Buchstaben fehlen in Titeln im PDF:** PowerPoint-Fehler ab dem 2. PDF-Export einer Sitzung. bippt startet
  PowerPoint deshalb je Export neu; sind eigene Präsentationen offen, bricht es ab → schließen und erneut.
- **Mac, Fehler -9074 / Zeitüberschreitung:** Freigabe fehlt oder Dialog offen → in PowerPoint nachsehen.
- **Windows:** PowerPoint per COM, keine Dialoge; läuft PowerPoint mit offenen Dateien, bleiben sie unberührt.
