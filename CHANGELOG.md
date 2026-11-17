# Changelog

Versions of the ppp plugin, newest first. Every published change raises at least the patch version and names here what changed; a learning session adds the lesson IDs as evidence (archive `knowledge/lessons/` in the ppp repository).

## 0.27.6 (2026-11-17)
- Hooks von VS Code unter Windows (PLUGIN PL-27): windows und powershell tragen dieselbe Zeile für Windows PowerShell 5.1, in der das Copilot-Runtime der Agents-Ansicht die Hooks startet; die Form mit && aus 0.27.2 bis 0.27.5 war dort ein Parserfehler, und der PreToolUse-Hook sperrte jeden Werkzeugaufruf
- ppp setup --check prüft, was ppp auf dem Rechner braucht (Python, git, pac, Playwright mit Edge und ffmpeg, python-docx, Word, die Pakete von bi-design); ppp setup --install installiert die fehlenden Python-Pakete und ffmpeg von Playwright (PLUGIN PL-29)
- Neuer Skill ppp-setup: prüft auf Zuruf („prüfe ppp“), auf einem neuen Rechner oder bei einem fehlenden Paket, fragt auf einer Karte und installiert
- ppp_hook.py liest die Eingabe der Hooks als UTF-8: ein Projektpfad mit Umlaut traf unter Windows kein Projekt, die Hooks taten still nichts
- Profil setup/ppp.code-profile (PLUGIN PL-28): installiert auch Python Environments, Pylance und Python Debugger, die der Import nicht nachzog

## 0.27.5 (2026-11-17)
- Einrichtung für neue Nutzer (PLUGIN PL-28): Profil setup/ppp.code-profile mit den Erweiterungen Power Platform Tools und Python, mit „Use for New Windows“ das Profil jedes neuen Fensters; README und Doku nennen den Installationslink vscode://chat-plugin/install?source=portolasas/ppp-plugin&plugin=ppp

## 0.27.4 (2026-11-17)
- Ein Hintergrund je Bericht (PLUGIN PL-25, Seqonis 17.11.): ppp pbi check meldet Seiten eines Berichts mit hellem und dunklem Hintergrund (R13), einen Visual-Kasten, der nicht zu seiner Seite passt, etwa ein weißes Deneb-Visual auf dunkelgrüner Seite (R14), und Text mit zu wenig Kontrast zu seinem Hintergrund (R15: Titel, Achsen, Legende, Textfeld, Slicer-Einträge, Karten, Tabellen, je auf ihrer eigenen Füllung); ein Visual ohne eigenen Hintergrund trägt den Kasten des Themes, Basis- und eigenes Theme werden je Eigenschaft zusammengeführt; die Seitenfarbe folgt den Vorgaben von Power BI (Seitenfläche ohne eigene Transparenz ist durchsichtig, es zählt das Hintergrundbild); ppp-power-bi › design.md: eine Fläche je Bericht, weiß oder Dunkelgrün, Farben mit Bedeutung sind Markenfarben, auch in einer Farb-Kennzahl
- bi-deneb: liest die Farbe der Seite aus dem Bericht und zeichnet auf Dunkelgrün mit eigenen Rollen der Marke (charts.json dark); embed schreibt die Seitenfarbe als Hintergrund des Visuals und verweigert ein für die andere Fläche gezeichnetes Visual, bevor es eine Seite anlegt; eine neue Seite übernimmt Hintergrund und Hintergrundbild des Berichts; eine vom Nutzer freigegebene Farbe (Brief colours) hält embed nicht an; R11 meldet ein Visual, das nicht auf seiner Seite sitzt; B1 (Farbe außerhalb der Marke) ist ein Fehler und hält embed an; B7 zählt Linien der Breite 0 nicht; B6 bewertet nur Text auf der Seite; der Boxplot zeichnet einen zusammengefallenen Median nicht mehr in der Standardfarbe von Vega-Lite
- bi-design: plattformen.md › Power BI nennt die Fläche je Bericht und die Markenfarben auf Dunkelgrün

## 0.27.3 (2026-11-17)
- Hooks von VS Code unter Windows (PLUGIN PL-27): der Starter hooks/ppp_hook.cmd findet unter C:\BITrusted auch eine Umgebung in <Ordner>\<Name> ohne envs, wie mamba create -p sie anlegt, nie aber im Paket-Cache pkgs von conda

## 0.27.2 (2026-11-17)
- Hooks von VS Code unter Windows (PLUGIN PL-27, nach dem Installationsfehler beim ersten Kollegen: Python aus Mamba außerhalb des PATH, jeder Werkzeugaufruf abgewiesen): sie starten über den neuen Starter hooks/ppp_hook.cmd, der das Python sucht (PPP_PYTHON, ~/.ppp/python.txt, python.exe im PATH ohne den Store-Platzhalter, eine aktivierte conda- oder mamba-Umgebung, C:\BITrusted, die üblichen Ordner von conda, mamba und miniforge, py) und immer mit 0 endet; ein PreToolUse-Hook, der scheitert, sperrt im Copilot-Runtime jeden Werkzeugaufruf. Das Feld windows kommt ohne Anführungszeichen und ohne ${PLUGIN_ROOT} aus (Node maskierte sie für cmd.exe, der Agent Host startete die Hooks unter Windows nie), dazu ein Feld powershell für das Copilot-Runtime; nie aus dem Arbeitsbereich
- ppp setup schreibt das Python, in dem es läuft, nach ~/.ppp/python.txt; der Werkzeugaufruf nennt ein Python außerhalb des PATH mit Pfad, für PowerShell oder bash zitiert

## 0.27.1 (2026-11-16)
- bi-deneb, aus dem Chargenvergleich in Seqonis (16.11., Lesson PBI-20261116-WIN-01): `bideneb live` schreibt eine Testseite, die eine Spezifikation im Browser in der Vega-Version von Deneb (6.4.0) ausführt, ihre Daten wechselt, wie es Slicer tun, und die per Klick erreichbaren Zustände (Seite, Sortierung) setzt; ein Visual, das danach leer bleibt, meldet sie (L0 bis L4). Den Blätterfehler der ersten Runde findet sie ohne Angaben im Brief. Warum die Visuals beim ersten Öffnen in Desktop leer waren, ist offen (Kopie ohne Daten vor dem Aktualisieren oder keine Größe beim ersten Einbetten; beides nicht belegt)
- ppp pbi check R12: ein Visual gehört zu einer Gruppe, die nicht auf seiner Seite liegt (Desktop löscht es beim Speichern; so verschwanden in Seqonis vier kopierte Slicer), oder `visualInteractions` nennen ein Visual, das es nicht gibt; ppp-power-bi › pbip.md nennt dazu den Kontrast kopierter Slicer und die leere Kopie ohne Aktualisierung
- bideneb check rendert auch zwei Zeilen und keine Zeile; R10 meldet Visuals einer Seite, deren Gruppe fehlt (Desktop löscht sie beim Speichern), und Interaktionen auf Visuals, die es nicht gibt; Farben, über die der Nutzer entschieden hat, stehen im Brief unter `colours` (B1 wird ein Hinweis); F1 meldet keine Felder mehr, die ein Mark aus einem anderen Mark liest; X3 zählt `fold` nicht mehr als Aggregation; die Config eines eigenen Vega-Visuals nennt die Schrift für Achsen, Legende und Titel

## 0.27.0 (2026-11-16)
- Zweites, wählbares Plugin bi-deneb im selben Marktplatz (PLUGIN PL-24): Skill und Agent bi-deneb mit dem Werkzeug bideneb bauen, prüfen und verbessern Deneb-Visuals für Power BI im Markendesign (17 Typen aus einem Brief und custom, lokaler Render mit erfundenen Zeilen, Prüfung von Feldern, Deneb-Regeln, Markenfarben, Kontrast und Text, Einbetten in PBIR); ppp setzt es nicht voraus und prüft an der Skill-Liste, ob es eingeschaltet ist
- ppp-power-bi: Markendesign immer (Theme von bi-designer, ohne bi-designer eine Karte) und Standard-Visuals zuerst; ein eigenes Visual (Deneb) nur für eine benannte Anforderung, mit Begründung in der README; neue Referenz design.md mit der Auswahl je Aussage (PLUGIN PL-25)
- ppp pbi check: R10 meldet einen Bericht ohne eigenes Theme, R11 nennt die Deneb-Visuals eines Berichts mit ihren Seiten
- Vorlage components/power-bi/README.md mit den Abschnitten Design und Custom visuals; ppp setup nennt das wählbare Plugin
- Drittes, wählbares Plugin bi-design im selben Marktplatz (PLUGIN PL-26): Skill bi-designer, Skills bi-inhalt und bi-ppt, Agent bi-ppt, Generator bippt und die Vorlagen ziehen aus dem Repo portolasas/bi-design (2.13.0) hierher und tragen die Version von ppp; ppp setzt es nicht voraus; ppp guide --kind deck findet bippt auch im Ordner neben ppp
- bi-deneb trägt die Farben des Markendesigns selbst (dieselbe tokens.json wie bi-design, ein Test hält sie gleich)

## 0.26.1 (2026-11-16)
- Korrekturen nach der unabhängigen Prüfung von 0.26.0 – ppp runs: der Server filtert nach den Flows des Projekts, jede Kennung in Klein- und Großschreibung (eine leere Antwort wird ohne diesen Filter für höchstens 24 Stunden wiederholt), jede abgefragte Spalte ist als gefüllt verlangt, ein Fehlertext ohne JSON über mehrere Zeilen wird zusammengefügt oder als nicht lesbar benannt, statt den Aufruf für alle Flows scheitern zu lassen; eine Partition, die mit einem Buchstaben beginnt, gilt nicht als Fehlercode
- Gehaltene Datei: gewartet wird nur bei einer Sperre (Windows: Sharing Violation), ein fehlendes Recht wird sofort gemeldet; ein gehaltenes Paket wird nicht zugunsten eines älteren übersprungen; die Meldung nennt ppp unpack nur für einen Export, nicht für ein Paket; pacs Entpacken wird nur wiederholt, wenn pac diese ZIP als gehalten nennt
- ppp connect: die Standardumgebung wird auch unter einem Alias ohne Datei nicht still genommen; bei einer benannten Umgebung wird die Rolle verlangt, bevor ppp den Tenant nach den Solutions fragt
- ppp import: die Warnung heißt no longer on after the import, weil sie auch einen Flow nennt, den der Tenant nicht mehr zeigt
- wdl_sim: parseDateTime weist Monats- und Tagesnamen als nicht nachgebildet ab und liest ein zweistelliges Jahr wie .NET bis 2049
- Skill-Texte: structure.md sagt, dass Terminate die letzte Aktion nach dem Schreiben des Protokolls ist und seine Meldung aus einem Filter über result('Try') kommt; ppp-diagnose, expressions.md und ppp-sessions gekürzt; ppp tidy --leftovers nennt in der Hilfe die leeren Ordner in changes/

## 0.26.0 (2026-11-16)
- ppp runs [<Flow>] [--hours N] [--failed] liest die Läufe der Flows des Projekts aus dem Tenant: Start (UTC), Status, Fehlercode und Fehlertext; nur lesend über pac env fetch (VERBUNDEN VB-21). Die Tabelle kennt den Lauf, nicht seine Aktionen; ppp-diagnose und ppp-package lesen die Läufe, bevor eine Karte danach fragt
- ppp-power-automate structure.md: ein Catch, der den Flow beenden darf, endet mit Terminate (Failed) samt Name und Fehler der gescheiterten Aktion aus result('Try'); ppp runs liest diesen Text
- ppp import: ein Flow, der nach dem Import an ist, ist keine Warnung mehr (Zeile On since this import); gewarnt wird nur, wenn der Import einen Flow ausgeschaltet hat
- ppp connect ohne Namen schreibt nichts, wenn in der Standardumgebung keine Solution des Projekts liegt, und verlangt den Namen der Umgebung auf einer Karte
- ppp check warnt bei einem Ordner in changes/ ohne Dateien, statt zu scheitern; ppp tidy --leftovers entfernt ihn
- Eine ZIP, die ein anderer Prozess hält, wird 20 Sekunden lang erneut gelesen (unpack, Paketprüfung, SHA-256); danach nennt die Meldung den Schritt (SOL-20261115-WIN-01)
- ppp setupflow schreibt Daten der Definition, die mit @ beginnen, als @@ in den Flow; expressions.md nennt die Regel (PA-20261115-WIN-01)
- wdl_sim: Switch, convertTimeZone, startOfMonth, dayOfMonth, isInt, parseDateTime, mod und SharePoint-Schreibzugriffe mit nometadata-Body; result() nennt zu einer gescheiterten Aktion die Antwort des Connectors oder den Fehler des Ausdrucks; ein unmögliches Datum ist ein Fehler des Flows (PA-20261115-WIN-02)
- ppp-power-automate teams-outlook.md: ListToDosByFolderV2 von Microsoft To Do liefert ein blankes Array, Seitenumbruch darauf scheitert, Vorgabe 10 Einträge (PA-20261115-WIN-03)
- ppp-sessions: ppp sessions ist der erste Aufruf, ohne Trockenlauf davor

## 0.25.0 (2026-11-14)
- Ebene über den Projekten (entwurf/HOME.md): ppp projects führt das Register der Projekte dieses Rechners, ppp catalog den Katalog bewährter Bausteine (proven in project.json), ppp settings --team --person, ppp team share und ppp projects --team den Team-Ordner; ppp-clarify fragt den Katalog ab
- ppp new package nimmt die Nummer der geplanten ROADMAP-Zeile mit dem Namen des Pakets, sonst die nächste freie (GEN-20261110-MAC-01)
- exchange in project.json (git, local): ppp storage --exchange git und ppp init --exchange git führen exchange/ und exchange/archive/ in Git, damit ZIPs den Rechner mit dem Tenant erreichen; ppp check nimmt ZIPs dann unter exchange/ an (PROJEKTSTRUKTUR S-3 geändert)
- components/power-automate/connectors/<name>/ für die Dateien eines Custom Connectors; ppp-power-automate: references/custom-connectors.md mit DLP-Gruppe und Code-Kapazität (GEN-20261110-MAC-02, PA-20261110-MAC-02)
- ppp verify C7 meldet pattern und patternProperties im Schema von Parse JSON in einem Flow mit Connector: der Import scheitert daran mit ActionSchemaNotSupported (PA-20261111-WIN-01)
- ppp pbi check M5 warnt vor Fehlerabfragen, die Fehler anzeigen in Desktop ins PBIP speichert; pbip.md nennt Ursache und Schutz (PBI-20261110-MAC-01)
- wdl_sim: Until, HTTP-Aktion über Lauf.http, weitere Connectoren über Lauf.connectoren, Mails in Lauf.mails, convertFromUtc, convertToUtc, formatDateTime, addToTime, addHours, addDays, dayOfWeek, isFloat, sort; SharePoint-REST mit $orderby, datetime im $filter, recycle() und ListItemEntityTypeFullName (PA-20261110-MAC-01)
- ppp-sessions: die Protokolle gehen immer ganz hoch; ppp-intake und ppp-clarify führen inputs/README.md als Übersicht mit Stand new und evaluated; ppp-package: ein Export vom anderen Rechner kommt mit git pull

## 0.24.0 (2026-11-14)
- Karte mit Code: jede Zeile CONFIRM FIRST endet mit --confirmed <code>; ppp import geht nur mit dem Code des jetzigen Stands weiter, sonst CHANGED und die neue Karte (Import, Rückspielen, Anlage, Umzug, Version heben)
- Im Modus large hebt ppp import --environment <ziel> --raise-version die Version der Hauptlösung nach einer Karte (pac solution online-version, Runde 3 O1), mit Eintrag in imports.jsonl
- Was nie beim Server ankam, verbraucht nichts: FAILED nur nach der Übergabe; ohne Übergabe, ohne Job nach 30 Minuten und bei DENIED bleibt die ZIP nutzbar. Eine Sperre je Projekt lässt nur einen Aufruf gegen den Tenant zugleich zu
- Drift: CRMServerServiceabilityVersion in Other/ zählt nicht; die Vorschau zählt Zeilen und zeigt geänderte vor verschobenen; Import record nennt die Zeile definition replaced als üblich; mehrzeilige Werte werden gelesen
- Umzugsziel mit Typ der Umgebung auf der Karte; ppp pack ändert bei bestehender ZIP nichts; ppp inventory findet im Modus large die Hauptlösung; ppp members nennt die Art; connected.py aufgeteilt (importlog.py, compare.py, cards.py, projectlock.py); Texte von ppp-package, ppp-intake und README nachgezogen

## 0.23.0 (2026-11-13)
- ppp import --create [--solution <Name> [--transfer]] legt eine leere Solution samt Publisher der Einstellungen an (Vorlage im Plugin), immer nach Karte; in Citizen Developments nur mit vorhandenem Publisher. ppp connect gleicht den Publisher mit den Einstellungen ab
- ppp members listet die Transferlösung und nimmt Flows, Umgebungsvariablen und Verbindungsreferenzen der Hauptlösung auf; ein Flow bringt seine Referenzen und Variablen mit
- Umzug nach Test: ppp connect --role test --target, ppp import --environment <ziel> mit Bindungen und Werten aus environments/<ziel>.json, immer nach Karte; ppp tenant --environment (--connections, --values), ppp export --compare --environment. Im Modus large nennen die Meldungen die Karte Version heben
- Hinweis nach RUNNING nennt den Befehl, der weiter wartet (Anlage, Rückspielen, Umzug); Umgebungsvariable PPP_HOME für einen eigenen persönlichen Ordner statt ~/.ppp (Erprobungen und Tests), auch für das Edge-Profil von ppp walk
- ppp-package: references/connected-create.md und connected-move.md

## 0.22.2 (2026-11-13)
- ppp verify (C9) meldet eine Funktion, die die Ausdruckssprache nicht kennt, als Fehler: Der Server nimmt einen solchen Flow an und schaltet ihn ein, erst der Lauf scheitert (Erprobung 13.11.)
- DRIFT und ppp export --compare zeigen je abweichender Datei die abweichenden Zeilen; nach einem gelungenen Import weisen ppp pack und ppp import ab, bis ppp export lief (ein ppp unpack derselben Version zählt)
- Karte beim ersten Import von ppp aus einem Projekt in eine Umgebung, auch wenn die Solution dort schon existiert; in eine Umgebung der Rolle test importiert ppp nur nach Karte
- ppp connect empfiehlt keine Entwicklungsumgebung mehr (Messungen der Runde 2 belegen keinen Zeitvorteil); Citizen Developments bleibt die Vorgabe, die Wahl liegt beim Nutzer. Usual here nennt für den Import die Dauer eines ganzen Aufrufs bis IMPORTED
- imports.jsonl trennt die Warnungen von ppp (ppp_warnings) vom Protokoll des Servers (record); Apps erscheinen je App statt je Datei; SessionStart erneuert den Werkzeugaufruf auch außerhalb eines ppp-Projekts
- ppp-package: references/connected.md geteilt, Drift, Fehler, Sperren und Rückspielen stehen in references/connected-trouble.md; ppp-intake und ppp-power-automate errors.md angeglichen

## 0.22.1 (2026-11-13)
- ppp import meldet IMPORTED erst, wenn die Version online und der Job dieses Imports beendet ist; bis dahin RUNNING mit Fortschritt (Nachtest V3: die Version stand online, während der Job noch lief)
- ppp connect verlangt die Rolle beim ersten Verbinden ausdrücklich (--role development|test|production, auch bei ppp init --environment); pac nennt sie nicht, die Regel über den Umgebungstyp entfällt; ohne Rolle importiert ppp import nicht
- ppp misst die Dauer seiner Exporte und Importe je Umgebung und zeigt sie in ppp connect, ppp tenant und bei RUNNING (Usual here: …); ppp connect empfiehlt bei Citizen Developments eine eigene Entwicklungsumgebung mit ungefähren Vergleichswerten aus den Versuchen
- Fehlermeldung eines gescheiterten Imports nennt den Grund von pac (The reason given was: …); ein von pac übersprungener Import (Version online nicht niedriger) verbraucht die ZIP nicht; ppp tenant --values behält Werte, die selbst eine Kennung sind; ppp check wartet auf den ersten pac-Aufruf 120 Sekunden
- ppp-package references/connected.md und ppp-intake an Rolle, Empfehlung, Zeitangaben und die Antworten des Imports angeglichen

## 0.22.0 (2026-11-13)
- Verbundener Modus (entwurf/VERBUNDEN.md): Ein Projekt mit environment in project.json exportiert und importiert selbst über pac; offline bleibt der Standard. ppp connect findet die Umgebung am Namen und schreibt Adresse, Rolle und Nutzung nach environments/<alias>.json; ppp init --environment und --confirm-import
- ppp export holt die Paket-Solution, entpackt und committet sie; --compare zeigt nur die Unterschiede; weist uncommittete Änderungen im Solution-Ordner immer ab, committete Arbeit, die der Tenant nicht hat, nur mit --force
- ppp import prüft Paket (SHA im Bericht), Version, committeten Solution-Ordner, Alter gegen den letzten Export, laufende Importe und Drift, legt eine Sicherung ab und liest das Ergebnis vom Server (Version, Protokoll, Flow-Status, Bindungen); Antworten IMPORTED, CONFIRM FIRST, DRIFT, RUNNING, FAILED; eine gescheiterte Version bleibt verbraucht; nie in eine Umgebung der Rolle production; --restore spielt die Sicherung zurück
- ppp tenant zeigt Versionen, ausgeschaltete Flows und Verbindungsreferenzen ohne oder mit gebrochener Verbindung; --log, --values, --write
- Hook vor dem Werkzeugaufruf: weist in einem verbundenen Projekt einen direkten pac-Aufruf ab
- Ein Export-Commit gleicher Version wird Prüfbasis; flüchtige Werte der meta.xml einer App zählen nicht als Änderung (C4, ppp unpack); ppp tidy lässt exchange/tenant/ aus; ppp check meldet eine abweichende Version im Tenant
- ppp-package: references/connected.md; ppp-intake fragt Anbindung und Karte vor dem Import ab; ppp-diagnose beginnt verbunden mit ppp tenant; Kernregeln: zwei Halbsätze
- Geschärft nach unabhängiger Prüfung: ppp connect verbindet nur am exakten Anzeigenamen, Typ Production ergibt die Rolle production; ein Import gilt nur mit dem Job dieses Imports als gescheitert oder 30 Minuten ohne Job; Fehlschläge im Importprotokoll sind eine WARNING-Zeile; AUTH, SYNTAX und BUSY verbrauchen die ZIP nicht
- Hook vor dem Werkzeugaufruf erkennt mehr Umwege (do, then, else, !, bash -lc, cmd /k, xargs, iex, dotnet pac) und gilt nur in Ordnern, deren project.json structureVersion und prefix hat
- Publisher: ppp settings --publisher-name, --publisher-display, --publisher-prefix, --publisher-option-prefix und --publisher-from; ppp init --publisher; project.json hält den Namen; ppp check und ppp unpack melden einen abweichenden Publisher; der SessionStart-Hook nennt ihn
- ppp-power-bi: references/visuals.md für Gantt und Zeitleisten (Wahl des Visuals, Segmenttabelle, Deneb, lokale Vorschau); pbip.md und reports.md ergänzt (GEN-20261111-WIN-01, GEN-20261111-WIN-02, PBI-20261111-WIN-01, PBI-20261111-WIN-02)

## 0.21.0 (2026-11-09)
- Ablage je Projekt (entwurf/ABLAGE.md): project.json hat storage (github, bitbucket, local), Strukturversion 2; bestehende Projekte einmal mit ppp migrate nachziehen, es trägt die Ablage aus dem Remote ein
- Ordner-Weg ohne Server: lokales Git ohne Remote, Commit nach jedem Schritt ohne Pull und Push; ppp init --storage local; ppp check meldet ein Remote als Fehler und warnt bei einem Ordner-Projekt in OneDrive, iCloud Drive, Dropbox oder Google Drive
- ppp backup sichert auf Zuruf den ganzen Verlauf als geprüftes Git-Bundle in den Sicherungsordner (ppp settings --backup), die letzten 10 bleiben, ppp backup --list zeigt sie; ppp check erinnert nach 7 Tagen; ppp restore stellt in einen neuen Ordner wieder her
- ppp storage zeigt und wechselt die Ablage, setzt oder entfernt das Remote und pusht nie; Bitbucket vorbereitet: neue Projekte beginnen bis zur Anbindung im Ordner-Weg
- ppp sessions lädt nur Chats aus GitHub-Projekten und nennt die übrigen als übersprungen
- Kernregeln: kein git pull und kein Push bei storage local; ppp-intake fragt die Ablage ab (references/storage.md); SessionStart nennt die lokale Ablage

## 0.20.1 (2026-11-07)
- ppp-docs: Schritt 6 verlangt references/guide.md vor dem ersten Bau aus dem Handbuch (Verhaltenstest 07.11.: der Agent las sie sonst nicht)
- ppp-docs references/deck.md nennt --bippt

## 0.20.0 (2026-11-07)
- SessionStart: Passt STATE.md nicht in den Kontext, kommen aktives Paket, nächster Schritt und manuelle Änderungen im Tenant zuerst; bisher fielen die manuellen Änderungen am Ende als Erstes weg
- ppp check warnt bei einer STATE.md über 6.000 Zeichen und nennt die Abschnitte, die die Vorlage nicht kennt
- ppp check: Fehlt das Original einer Konfliktkopie, nennt die Meldung git checkout -- <Datei>
- README: Unter Windows muss python im PATH stehen; nur mit dem Starter py landen Hooks und Werkzeugaufruf beim Platzhalter des Microsoft Store

## 0.19.0 (2026-11-07)
- ppp-app-walk aufgeteilt: der Ablauf bleibt im Skill (10,4 statt 21,5 KB), Felder und Aktionen, Befunde, Rollen und Belege stehen in references/ (PL-23)
- ppp-docs: ppp guide in references/guide.md, das Schulungsdeck in references/deck.md (9,6 statt 11,4 KB)
- Kernregeln 6.315 statt 6.492 Zeichen: design.md-Hinweis in ppp-package, Modell-ID in der Regel für Subagenten, Prüfung auf Widersprüche nur noch in ppp-clarify
- Größenbudgets als Test: SKILL.md 12.000, Referenz 8.000, Zeile 1.000 Zeichen (PL-23)
- ppp guide findet bippt im Klon von bi-design auch mit dem Plugin im Wurzelverzeichnis (bi-design 2.13.0)

## 0.18.2 (2026-11-07)
- Claude Code unter Windows: Hook-Befehl fällt von python3 (oft nur der Platzhalter des Microsoft Store) auf python zurück, sonst kamen die Kernregeln nie an; Claude Code kennt kein Feld windows
- ppp check meldet Konfliktkopien von OneDrive und iCloud (name(1).ext, name 2.ext, name-RECHNER.ext) neben einer versionierten Datei, als Fehler wenn das Original fehlt
- README: 15 Skills

## 0.18.1 (2026-11-06)
- ppp pbi check: eine R7-Meldung je fehlender Tabelle, Spalte oder Measure mit Zahl der Verweise, gleiche Meldungen nur einmal, Seitenfilter mit Datei
- ppp pbi folgt den Verweisen der .pbip auf den Berichtsordner und nennt fehlende Ordner; Warnung P2 bei PBIP in OneDrive (Erprobung Seqonis 06.11.)

## 0.18.0 (2026-11-06)
- ppp pbi list und check: Power BI als PBIP (TMDL, PBIR), Feldreferenzen gegen das Modell, Namen, BOM, $schema, Zeitfunktionen, .pbi-Dateien in Git (PLUGIN PL-22)
- ppp-power-bi mit references/pbip.md; .gitignore-Vorlage und ppp check mit .pbi/cache.abf und .pbi/localSettings.json

## 0.17.0 (2026-11-06)
- Haltepunkt: Starttext steht im Chat über der Karte, nie im Kartentext – eine beantwortete Karte zeigt ihren Text nicht mehr (Nutzer 06.11.)
- ppp guide --word unter Windows: Pfad über PPP_WORD_FILE, powershell -Command gab keine $args weiter und Word bekam keine Datei
- ppp walk: expect mit "stop": true beendet den Walk; --check verlangt vor einem schreibenden Klick mit nth einen solchen expect mit derselben nth (PAPPS-20261105-WIN-03)
- ppp walk scrollt nach einem markierten Bild die verschobenen Container zurück; markiert abweichend, unmarkiert nachstellen (GEN-20261105-WIN-04)
- ppp walk: Nummer einer Markierung bleibt im App-Rahmen, Position in report.json (GEN-20261105-WIN-03)
- ppp walk legt einen nicht löschbaren previous-Ordner als previous-<Zeit> beiseite (GEN-20261105-WIN-02)
- ppp walk vergleicht Bilder mit bis zu 2 px Größenunterschied auf der gemeinsamen Fläche
- ppp-docs: verdeckter Folientext steht noch im PDF-Text, nur das gerenderte Bild zählt (GEN-20261105-WIN-05)

## 0.16.2 (2026-11-05)
- ppp guide --kind deck: Aufgabenfolien mit Nummernmarken und Ergebnis-Kasten, Kartenfolien und Übungen als Zeilen über die ganze Folie, Prognose-Erklärung in Spalten; vorsichtige Höhenschätzung, kein Text mehr außerhalb seiner Fläche

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
