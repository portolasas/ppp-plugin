---
name: bi-ppt
description: BI-PPT – erstellt PowerPoint-Präsentationen im Boehringer-Ingelheim-Design (offizieller BI-Master v2.1) aus gegebenen Informationen (Transkripte, Projektaufträge, Notizen, Excel), erzeugt neue angepasste Versionen bestehender Präsentationen (z. B. Projektteam-Update → Steering-Committee-Update) ändert einzelne Folien bestehender Decks gezielt und wandelt Präsentationen in fremdem Design ins BI-Design um. Schreibt zu jedem Deck die Folienbeschreibung <Name>.md (Inhalt und Gestaltung je Folie). Arbeitet mit Spezifikation (JSON) + Generator bippt (Folientypen Status, Vergleich, Prozess, Timeline/Gantt, Maßnahmen, Kennzahlen, Diagramm, Tabelle …), prüft Brand-Regeln und rendert zur Sichtprüfung. Laden bei jeder Anfrage zu Folien, Präsentation, Deck, PowerPoint, PPT, Steering-/Projekt-Update, „im BI-Design“, „Folien umwandeln“ oder „Folie ändern“.
---

# BI-PPT – Präsentationen im BI-Design

Werkzeug: `bippt` (Python ≥ 3.9 mit python-pptx) liegt im Plugin **bi-design** unter `<plugin>/tools/bippt.py`;
`<plugin>` ist der Ordner zwei Ebenen über dieser SKILL.md (`<plugin>/skills/bi-ppt/SKILL.md`).
- Erster Aufruf wie bei ppp: macOS `python3 "<plugin>/tools/bippt.py" umgebung` · Windows (PowerShell)
  `python "<plugin>\tools\bippt.py" umgebung`; nicht `py`. Anders als ppp **ohne `-I`**: `-I` blendet die mit
  `pip --user` installierten Pakete aus.
- `bippt <befehl>` steht im Folgenden für den Aufruf, den `bippt umgebung` in der Zeile `Aufruf` nennt (absoluter Pfad
  des Interpreters, der die Pakete hat). Je Sitzung einmal ermitteln, nicht raten; er ändert sich mit jeder Plugin-Version.
- Marke (Farben, Icons): Skill **bi-designer** im selben Plugin (`marken/<profil>/tokens.json`, `icons.txt`); Custom
  Colors des BI-Masters (Gray 1–8, Signal Red/Yellow/Green) liest bippt aus der Vorlage. Nie Farben frei erfinden.
- Vorlage: `<plugin>/vorlagen/BI_Vorlage_16x9.pptx` (BI-Master v2.1); eigene über `bippt konfig --setze vorlage=<pfad>`.
- Folienbibliothek: `<plugin>/vorlagen/BI_Slide_Library.pptx` (offizielle BI Slide Library, 184 gestaltete Folien,
  gleicher Master) – Übersicht und Ablauf in [reference/bibliothek.md](reference/bibliothek.md), Formen je Folie mit
  `bippt katalog --folien n`.
- Einstellungen je Rechner: `~/.bi-design/config.json` (`bippt konfig`), u. a. `asset_root` (Logos, Icons).

Antworte deutsch, sachlich, knapp. Grundsatz: **teuer denken, billig bauen** – Inhalt und Storyline gründlich,
Umsetzung immer über Spezifikation + `bippt bauen` (nie Formen einzeln per Hand-Skript), Änderungen = Spec ändern.

Zu jeder Präsentation gehören drei Dateien nebeneinander: `<Name>.pptx`, `<Name>.spec.json` (Eingabe des Generators) und
die **Folienbeschreibung** `<Name>.md` – Typ, Gestaltung, Kernaussage, Inhalt und Notizen je Folie, damit andere Agenten
und Sitzungen das Deck lesen, ohne die PPTX auszulesen. `bippt bauen` schreibt sie bei jedem Bau; bippt pflegt nur den
Abschnitt zwischen `<!-- bippt:folienbeschreibung … -->` und `<!-- /bippt:folienbeschreibung -->`, Text außerhalb bleibt.

## 0. Start (jede Sitzung, 1 Befehl)
`bippt umgebung` → muss mit `ERGEBNIS: OK` enden. Sonst je Meldung:
- `FEHLT Paket …`: auf einer Karte um Zustimmung bitten, dann `bippt einrichten` (pip `--user`, kein venv).
- `ALT …`: alte Kopien von BI-PPT 1.x oder PPP 0.17 verdecken das Plugin. Karte, dann `bippt aufraeumen --ja`;
  danach VS Code neu laden bzw. neue Claude-Code-Sitzung.
- alles andere: [reference/installation.md](reference/installation.md).

Liegt der Arbeitsordner in einem Git-Repo (`git rev-parse --show-toplevel` gelingt), danach `git pull`.

## 1. Modus erkennen
| Modus | Auslöser | Ablauf |
|---|---|---|
| **I – Inhalt** | neue Präsentation ohne fertigen Inhalt, oder „Inhalt ausarbeiten“ | Skill **bi-inhalt**, danach N mit Briefing |
| **N – Neu** | Briefing, Infos oder Quellen, keine Basis-PPT | §2 → §3 → §4 |
| **V – Neue Version** | bestehende PPT als Grundlage („auf Basis von …“, Update für anderes Gremium) | §2 → §3 mit `basis` → §4 |
| **Ä – Ändern** | einzelne Folien eines bestehenden Decks korrigieren, ergänzen, umstellen | §2 → §3a → §4 |
| **U – Umwandeln** | PPT in fremdem/altem Design → BI-Design, auch Decks aus der Erstellen-Funktion von Copilot | [reference/umwandeln.md](reference/umwandeln.md); gut gestaltete Decks mit `bippt umwandeln marke` |
| **P – Prüfen** | „passt das zum Brand?“ | `bippt pruefen` + `bippt rendern` → Befunde mit Folie, Regel, Fix |

Neue Präsentation ohne Briefing und ohne fertige Folienliste: zuerst fragen „Inhalt erst gemeinsam ausarbeiten (Empfehlung) oder
direkt bauen?“. **Mit Briefing** (`<Name>_Inhalt.md` aus bi-inhalt) ist der Inhalt abgenommen: Titel und Inhalte wörtlich
übernehmen, Bildform umsetzen, keine neue Rückfragerunde außer zu `Offen:`.

## 2. Verstehen (token-sparsam)
1. **Bestehendes Deck (Modus V und Ä) zuerst über seine Folienbeschreibung:** `<Name>.md` neben der PPTX (erste Zeile
   `<!-- bippt:folienbeschreibung`) oder das `dokument` der Spec daneben. Sie ersetzt das Einlesen des Decks: kein
   `bippt lesen` und kein `bippt analyse` der ganzen PPTX. Das Deck nur für die Folien ansehen, die sich ändern und deren
   Einzelheiten die Beschreibung nicht nennt: `bippt analyse <pptx> --formen --folien 3,7` (id, Name, Läufe für
   `aendern`) bzw. `bippt rendern <pptx> --folien 3,7`. Ohne Folienbeschreibung: `bippt beschreiben <pptx>` legt sie an,
   dann sie lesen. Formen, die python-pptx nicht kennt (früherer Platzhalter ohne Geometrie, Freihand, SmartArt), meldet
   `analyse` bzw. `pruefen` als „Unbekannt“/HINWEIS – ihr Text wird gelesen, sonst werden sie übersprungen.
2. Quellen nur über `bippt lesen <dateien…> -o <arbeitsordner>/_quellen.md` (VTT, DOCX, PPTX, PDF, XLSX) und
   die Datei dann gezielt lesen. Eine **Vorlage**, die die Folien schon Folie für Folie beschreibt (z. B. von ppp), ist
   Hauptquelle und wird zur Folienbeschreibung: `"dokument": "<pfad>"` in der Spec; bippt hängt seinen Abschnitt an und
   lässt ihren Text stehen. Ein Dokument, das nur Stoff liefert (Handbuch, Konzept), ist Quelle wie jede andere.
3. Ordner, die der Nutzer ausschließt (z. B. `Archiv/`), nie öffnen. Aktuellste Quelle hat Vorrang
   (z. B. Monolog/Transkript vor Projektplan vor alter Präsentation) – Widersprüche nicht still auflösen.
4. **Eine gebündelte Rückfragerunde** (Tool ask_user / AskUserQuestion, je Frage Empfehlung zuerst) nach
   [reference/fragen.md](reference/fragen.md): nur was Inhalt oder Gestaltung wirklich ändert – Datum, Publikum/Zweck,
   Status/Ampeln, Konflikte zwischen Quellen (mit Zitat beider Stellen), Termine, Entscheidungsbedarf, Umfang.
   Alles andere mit Standard entscheiden und im Abschluss nennen. Bei Konflikten oder Unsicherheiten immer fragen.

## 3. Storyline und Spezifikation
1. Storyline nach [reference/arbeitsweise.md](reference/arbeitsweise.md) (Publikum → Folienzahl, Aktionstitel,
   eine Kernaussage je Folie als Band, Details ins ausgeblendete Backup).
2. **Storyboard** nach [reference/bibliothek.md](reference/bibliothek.md) › Bildform zuerst: je Folie Aussage, Bildform,
   Quelle (`bib n`, `layout`, `typ`). Gleich gebaute Inhalte bekommen dieselbe Folie, eine neue Bauart nur bei einer anderen
   Art von Aussage. Fertig, wenn jede Inhaltsfolie eine Bildform hat. Für jede Bibliotheksfolie `bippt katalog --folien n`
   lesen, jeden Blindtext füllen und Beispiel-Icons durch passende ersetzen (`"bilder": {"<id>": "icon:<name>"}`).
3. Spezifikation `<Name>.spec.json` **neben die Ausgabe** schreiben (Startgerüst: `bippt neu <ordner> --name <Name>`).
   Folientypen und Felder: [reference/folientypen.md](reference/folientypen.md) (`bippt typen`). Icons: `bippt icons <begriff>`.
   Kopf mit `zweck` (Anlass, Publikum, Datum) und `quellen`; je Folie `beschreibung`, wenn Typ und Felder die Gestaltung
   nicht zeigen (Bildinhalt, Anordnung einer Basisfolie) – beides steht dann in der Folienbeschreibung.
4. Modus V: `"basis": "<alte.pptx>"`, `ausgabe` eine neue Datei; jede Folie entweder neu (`"typ"`) oder `{"basis": n,
   "ausblenden"?, "ersetzen"?, "platzhalter"?, "aendern"?, "elemente"?}`. Basisfolien behalten Inhalt und Sichtbarkeit,
   bis die Spec etwas ändert; nicht aufgeführte Basisfolien entfallen. Titel-Folie der Basis über
   `platzhalter` aktualisieren. Bild tauschen (Zuschnitt bleibt), Absätze ergänzen, Läufe im Band, Formen verschieben
   oder entfernen: `aendern`; neue Formen auf der Basisfolie: `elemente` ([reference/folientypen.md](reference/folientypen.md)
   › Basisfolien). Nie ein eigenes python-pptx-Skript zum Nacharbeiten.

## 3a. Ändern (Modus Ä) – nur die betroffenen Folien
1. Aus Auftrag und Folienbeschreibung die **betroffenen Folien** bestimmen (Nummern); ist das mehrdeutig, in der
   Rückfragerunde klären. Fertig, wenn die Liste feststeht.
2. Spec daneben: nur die Einträge dieser Folien ändern, `bippt bauen <spec>`. Die übrigen Folien entstehen aus
   unveränderten Einträgen identisch neu.
3. `bippt bauen` bricht mit `ABBRUCH: … nach dem letzten Bau geändert (Folie …)` ab (Deck z. B. in PowerPoint
   bearbeitet), oder es gibt keine Spec: neue Spec mit `"basis": "<deck>.pptx"` und neuer `ausgabe`
   (`<Projekt>_<Anlass>_<TT.MM.JJJJ>.pptx`, sonst Endung `_v2`), alle Folien als `{"basis": n}`, die betroffenen mit
   `ersetzen`/`aendern`/`elemente` oder als neuer `typ`. So bleiben die Handänderungen. `--erzwingen` verwirft sie –
   nur, wenn der Nutzer das auf einer Karte gewählt hat.
4. Fertig, wenn die Zeile `ÄNDERUNGEN` von `bippt bauen` genau die betroffenen Folien nennt. Nennt sie mehr, die
   Ursache in der Spec suchen (z. B. geändertes `heute` verschiebt Timelines) und beheben.

## 4. Bauen – Prüfen – Sehen (max. 3 Runden)
```
bippt bauen <Name>.spec.json          → ERGEBNIS: OK | Warnungen (Überlauf, Titel zweizeilig, Wort zu breit,
                                        Tabelle zu hoch, Icons, Timeline-Beschriftung, Bild unscharf oder BI-Logo,
                                        Text zu lang für seine Form, Fläche halb leer, Blindtext, Einzelwörter, Umlaute, Eintönigkeit);
                                        BESCHRIEBEN <Name>.md, ÄNDERUNGEN je Folie seit dem letzten Bau
bippt pruefen <Name>.pptx --woerter N → ERGEBNIS: OK (keine FEHLER; N nach Publikum)
bippt rendern <Name>.pptx [--alle]    → kontaktbogen.png ansehen, nur auffällige Folien einzeln (folie_NN.png)
bippt sichten <Name>.pptx             → misst am Render: Überlappung, Überstand, große leere Flächen; für Umgebungen ohne Blick auf die Bilder
```
Sichtprüfung je Folie: nichts überlappt/abgeschnitten, Text lesbar (≥ 9 pt im Inhalt), Kernaussage stimmt,
Ampeln/Termine = Quellen, keine leeren Flächen > ⅓ Folie. Fixes immer in der Spec, dann neu bauen.
Rendern auf dem Mac: PowerPoint muss ohne offene eigene Präsentationen sein (bippt startet es frisch und beendet es);
der Ordner `~/Documents/BI-PPT-Render` ist einmalig in PowerPoint freigegeben – nie andere Ordner an PowerPoint geben.
Kein Renderweg? Dann nur `pruefen` und das im Abschluss sagen.

## 5. Abschluss
- Ausgabe neben die Quellen (oder wohin der Nutzer sagt); Dateiname `<Projekt>_<Anlass>_<TT.MM.JJJJ>.pptx`;
  Spec und Folienbeschreibung daneben lassen (spätere Änderungen = Spec + `bippt bauen`, die Beschreibung folgt).
  Eigene Hinweise zur Folienbeschreibung außerhalb der Marken schreiben. `_render_*`-Ordner und `_quellen.md` löschen,
  wenn der Nutzer sie nicht braucht.
- **Sichern wie bei ppp:** Im Git-Repo nach jedem abgeschlossenen Schritt ohne Rückfrage committen und nach `main`
  pushen. Schritte: Deck gebaut und geprüft (§4 fertig), Änderung fertig (§3a Schritt 4), Umwandlung fertig – ein Commit
  je Schritt, nicht je Korrekturrunde. Stagen nur die Dateien des Decks: PPTX, Spec, Folienbeschreibung (bzw.
  `dokument`) und neu abgelegte Bilder; `_render_*`-Ordner und `_quellen.md` bleiben draußen. Nachricht
  `<Name>: <was sich geändert hat>`, z. B. „SC-Update 12.11.: Termin auf Folie 4“. Push abgelehnt: `git pull --rebase`,
  erneut pushen. Ohne Remote nur committen; steht das Repo auf einem anderen Branch, dort committen und pushen und das
  im Abschluss nennen.
- Antwort: Pfade (PPTX, Spec, Folienbeschreibung) · Folienliste (sichtbar/Backup) mit je einer Zeile Inhalt · bei
  Modus V/Ä die geänderten Folien laut `ÄNDERUNGEN` · getroffene Annahmen · offene Punkte · Prüfergebnis (`pruefen`,
  Render ja/nein) · Commit und Push (Kurz-Hash) oder „kein Git-Repo“.

## 6. Regeln (BI-Master v2.1 + bi-designer)
- **Der Master ist verbindlich** (How-to slides, vor jedem Referenzdeck): nur Layouts der Vorlage, nur Theme- und Custom
  Colors, **keine Abstufungen** (heller/dunkler x %) und keine Standardfarben; Ampel = Signal Green/Yellow/Red, Gelb–Rot
  = `YR`; Akzentgrün nie als Text/dünne Linie/Rahmen auf Hell (nur auf Dunkelgrün oder als Fläche hinter dunkelgrünem Text).
- Texte und Storyline nach [reference/arbeitsweise.md](reference/arbeitsweise.md) › Texte; `bippt pruefen --woerter` je
  Publikum (Steering 120, Projektteam 200).
- Schriften = Theme (Boehringer Forward Head/Text); Textebenen 1–4 16 pt, ab Ebene 5 12 pt im Fließtext-Layout.
- Fußzeile: `<Präsentationstitel>     |     <Vertraulichkeit>` (Standard „ONLY FOR INTERNAL USE“); Titelfolie nur Vermerk.
- Icons nur aus dem Brand-Set, Variante nach Hintergrund. Logo kommt aus dem Master – nie selbst einfügen.
- Nicht im Paket definiert (Bildsprache, Freiraum) → „(offen, Brand Hub prüfen)“ statt raten.

## 7. Erweitern
Nur im Repo von ppp (Ordner `plugin/bi-design/`), nie in der installierten Kopie. Neuer Folientyp: Funktion mit `@folientyp("name")` in
`tools/bippt/folien.py` (Bausteine aus `bausteine.py`), Inhalt und Gestaltung für die Folienbeschreibung in
`beschreiben.py`, Doku-Zeile in `reference/folientypen.md`, Beispiel in
`beispiele/beispiel.spec.json`, Tests grün (`tests/bidesign/run.py`), Version mit `tools/version.py bump` des Repos von ppp erhöhen (nie von Hand in den Manifesten), Eintrag im CHANGELOG von bi-design, Commit direkt nach `main`.
Neue Marke: Profil in bi-designer + eigene Vorlage (`bippt vorlage <deck> -o …`).
