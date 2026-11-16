# Spezifikation und Folientypen

Vollständiges Beispiel mit allen Typen: [../beispiele/beispiel.spec.json](../beispiele/beispiel.spec.json) (`bippt neu`);
Projektteam-Update nach Referenzdeck: [../beispiele/projektteam.spec.json](../beispiele/projektteam.spec.json).

## Kopf der Spezifikation
| Feld | Bedeutung |
|---|---|
| `ausgabe` | Dateiname/Pfad der PPTX (relativ zur Spec) |
| `fusszeile` | Präsentationstitel in der Fußzeile (z. B. „Projekt \| Projektteam-Update“); Vermerk wird angehängt: `Titel     \|     ONLY FOR INTERNAL USE` |
| `vertraulichkeit` | Vermerk (Standard aus config, „ONLY FOR INTERNAL USE“); `""` = keiner |
| `heute` | Datum der Heute-Linie in Timelines (Standard: heute) |
| `vorlage` | andere Vorlage (Standard: BI-Master v2.1) |
| `basis` | bestehende PPTX (Modus V) – dann ist sie Vorlage und Folienquelle |
| `marke` | bi-designer-Profil (Standard boehringer-ingelheim) |
| `bibliothek` | andere Folienbibliothek für `bib` (Standard: BI Slide Library aus dem Plugin) |
| `zweck` | Anlass, Publikum, Datum in einem Satz – Kopf der Folienbeschreibung |
| `quellen` | Dateien, aus denen der Inhalt stammt – Kopf der Folienbeschreibung |
| `dokument` | Folienbeschreibung (`.md`, relativ zur Spec), nur für eine vorhandene Vorlage (z. B. von ppp); Standard `<ausgabe>.md` |
| `folien` | Liste der Folien in Reihenfolge |

## Felder jeder neuen Folie
`typ`, `titel`, `band` (`"Text"` fett oder `{"label": "…:", "text": "…", "stil": "dunkel|akzent|hell"}`, höchstens zwei Zeilen;
`dunkel` = Position/Entscheidung, `akzent` = Gesamtaussage der Statusfolie, `hell` = Kernänderung, kritischer Pfad, Fazit),
`quelle` (Quellenzeile unten; Inhalt und Band enden dann darüber), `notizen`, `beschreibung` (nur in der Folienbeschreibung: Gestaltung, die Typ und Felder nicht zeigen),
`ausblenden`, `ab_hier_ausblenden` (z. B. am Backup-Kapitel), `dunkel` (dunkle Layoutvariante, wo vorhanden),
`layout` (Layout-Kurzname erzwingen), `fusszeile: false`.

Text überall: `"… **fett** … ==hervorgehoben== …"`, Liste = mehrere Absätze, oder
`{"t": "…", "fett": true, "groesse": 12, "farbe": "DG", "punkt": true, "ebene": 1}`.
Farben als Kürzel: DG, AG, WH, LG, WG, YEL, MYEL, LRED, RED, MRED, DRED, LBLU, BLU, MBLU, DBLU, LVIO, VIO, MVIO, DVIO,
SGRN, SYEL, SRED, G1…G8 – oder Token-Namen aus bi-designer. Keine Abstufungen (Master: nicht CD-konform).
Ampelwerte: G, Y, R, N und YR (Gelb–Rot: Verzug, Eskalation erwartet; halb gelb, halb rot).

## Bibliotheksfolien (`bib`)
`{"bib": n, "titel": "…", "texte": {"id": "…" | ["Absatz", …]}, "bilder": {"id": "foto.jpg"}, "daten": {"id": {"kategorien",
"reihen", "titel"}}, "tabellen": {"id": [[…], …]}, "entfernen": [id]}` kopiert Folie n der Folienbibliothek (Kopf
`bibliothek`, Standard aus dem Plugin) und füllt sie; danach wirken `ersetzen`, `platzhalter`, `aendern`, `elemente` wie
bei Basisfolien. ids: `bippt katalog --folien n`. Übersicht, Regeln und Ablauf: [bibliothek.md](bibliothek.md).

## Basisfolien (Modus V)
`{"basis": 7, "ausblenden": true, "ersetzen": {"alter Text": "neuer Text"}, "platzhalter": {"1": ["Zeile 1", "Zeile 2"]}, "titel": "…"}`
`ersetzen` findet Text auch über Läufe hinweg; Läufe außerhalb des Treffers behalten ihr Format. Alle Einträge wirken in
einem Durchgang von links nach rechts (bei gleicher Stelle gewinnt der längere Suchtext): Eingesetzter Text wird nicht noch
einmal ersetzt, auch wenn er einen Suchtext enthält (`"GBS": "GBS United"`). `bauen` warnt nur für Einträge, die auf der
Folie wirklich fehlen. Basisfolien behalten
ihre Sichtbarkeit; `"ausblenden": true|false` ändert sie. `beschreibung` wie bei neuen Folien. `ausgabe` ist immer eine
neue Datei, nie die Basis selbst (sonst wendet jeder Bau `ersetzen` und `aendern` erneut an; bippt bricht ab).

**Einzelne Formen ändern** – `"aendern": [{…}, …]`, Reihenfolge wie angegeben; Namen, ids und Läufe aus
`bippt analyse <basis.pptx> --formen`. Ansprechen: `"form": "Name"` (bei doppeltem Namen `"nr": 2`), `"id": 12` oder
`"formen": ["Name", …]` (z. B. eine Reihe). Je Eintrag beliebig kombinierbar:

| Feld | Wirkung |
|---|---|
| `x`, `y`, `w`, `h` · `dx`, `dy` | Lage und Größe in Zoll, absolut bzw. relativ |
| `bild`, `ausschnitt` | Bild in Bildform oder Bildplatzhalter tauschen (Pfad relativ zur Spec). Rahmen bleibt, das Bild füllt ihn ohne Verzerrung. Ohne `ausschnitt`: gleiches Seitenverhältnis → gleicher Zuschnitt, sonst an derselben Kante wie bisher; sonst `oben`, `mitte`, `unten`, `links`, `rechts` oder `{"oben_px": 586}` / `{"links_px": n}` (Pixel des neuen Bildes) |
| `absaetze` | alle Absätze: `["Text", null, {"t": "Text", "wie": 2}]`; `null` = Absatz bleibt; überzählige alte entfallen |
| `anhaengen` | Absätze anhängen (Format des letzten oder `wie`) |
| `absatz` + `text` | einen Absatz (ab 1) setzen |
| `absatz` + `laeufe` | Läufe des Absatzes einzeln: `["Label:  ", null]`; `null` = Lauf bleibt, `{"t", "wie": n}` = neuer Lauf im Format von Lauf n |
| `absatz` + `entfernen: true` | Absatz bzw. Liste von Absätzen entfernen |
| `name` · `entfernen: true` | umbenennen · Form entfernen |

Text ohne Markierung bekommt das Format des ersten Laufs im Absatz; `**fett**` übernimmt das Format eines fetten Laufs, der
Rest das eines normalen – so bleibt gemischte Formatierung (Band: Label fett, Text normal). Fehlt eine Form oder ist sie
mehrdeutig, warnt `bippt bauen` und lässt sie aus.
```json
{"basis": 10, "aendern": [
  {"form": "Picture Placeholder 4", "bild": "bilder/screenshot_01.png", "ausschnitt": "oben"},
  {"form": "TextBox 9", "anhaengen": ["Ein dritter Punkt im Format des zweiten"], "h": 1.4},
  {"formen": ["TextBox 10", "TextBox 11"], "dy": 0.4},
  {"form": "Kernaussage", "laeufe": [null, "Neue Frage an die Runde?"]}]}
```

**Neue Formen auf der Basisfolie** – `"elemente"` wie im Typ `frei`, z. B. ein helles Band als Untertitel:
`{"form": "band", "label": "Heute:", "text": "…", "stil": "hell", "y": 1.43, "h": 0.44}`.

`"farben_angleichen": true` (je Folie) bzw. `"basis_farben_angleichen": true` (Kopf) setzt Nicht-Markenfarben und Abstufungen
von Designfarben alter Folien auf die nächste Markenfarbe – sinnvoll, wenn `bippt pruefen` „Farben außerhalb der Marke“
oder „Abstufungen“ in Basisfolien meldet. Danach im Render prüfen.

## Folienbeschreibung und Baustand
`bippt bauen` schreibt neben die PPTX `<ausgabe>.md` (oder in `dokument`): je Folie Typ, Gestaltung, Kernaussage, Inhalt
und Notizen – neue Folien aus der Spec, unveränderte Basisfolien aus der Folienbeschreibung der Basis, sonst aus dem Deck.
bippt pflegt nur den Abschnitt zwischen `<!-- bippt:folienbeschreibung … -->` und `<!-- /bippt:folienbeschreibung -->`.
Die Startmarke trägt je Folie einen Fingerabdruck (`bau=`, `stand=`; Text, Lage, Bilder, Tabellen, Notizen, Sichtbarkeit).
Damit meldet `bauen` die Zeile `ÄNDERUNGEN` und bricht ab, wenn das Deck nach dem letzten Bau geändert wurde
(`--erzwingen` überschreibt). Reines Öffnen und Speichern in PowerPoint ändert den Fingerabdruck nicht.
`bippt beschreiben <pptx>` beschreibt ein Deck ohne Spec oder nach Handänderungen; der Baustand bleibt.

## Typen
| typ | Layout | Felder | Einsatz |
|---|---|---|---|
| `titel` | Title slide (bright) / `dunkel` | `titel`, `untertitel` [Zeilen] | Titelfolie |
| `agenda` | Agenda | `punkte`; Titel ohne Angabe „Agenda“ | Agenda |
| `kapitel` | Chapter divider (1) / `dunkel` | `titel`, `untertitel` | Abschnitt, „Backup“ |
| `text` | One content | `punkte` (mit `ebene`) | Fließtext/Aufzählung im Master-Stil |
| `status` | Only title | `phasen` [Namen], `straenge` [{`titel`, `ampel`, `stand` [2=fertig,1=aktiv,0=offen], `punkte`, `naechster`}], `legende` {G: …, YR: …} | Status je Strang |
| `vergleich` | Only title | `spalten` [3], `zeilen` [[thema, alt, neu]]; Zelle `{"ampel": [..], "labels": [..]}` | Änderungen alt → neu |
| `prozess` | Only title | `kopf` {label,text}, `schritte` [{`icon`, `titel`, `text`, `status`}], `hinweis`, `hinweis_ab`, `karten`, `hoehe`, `groesse` (Schritttext, Standard 9,5 bzw. 10,5 in Schrittkarten), `kopf_groesse` (Titel in Schrittkarten, 11,5); mit `ueber`/`punkte` je Schritt → Schrittkarten (unten) | Ablauf/Prozesskette, Vorgehen, Eskalationslogik |
| `karten` | Only title | `kopf`, `karten` [{`titel`, `ampel` \| `akzent`+`icon`, `stil` leiste/akzent/ohne, `hell`, `hervor`, Blöcke}], `hoehe` inhalt (Standard) / voll | 2–4 Bereiche nebeneinander, Varianten |
| `timeline` | Only title | `skala` woche/monat/quartal (auto: ≤ 190 Tage Wochen, ≤ 18 Monate Monate, sonst Quartale), `von`, `bis`, `heute`, `zeilen` [{`titel`, `elemente`}], `marker`, `schatten`, `legende`, `fakten` \| `boxen` | Gantt/Roadmap |
| `massnahmen` | Only title | `zeilen` [{`wann`, `was`, `details`, `tag`}], bis ca. 8 Zeilen | Nächste Schritte |
| `tabelle` | Only title | `kopf`, `zeilen`, `breiten`, `groesse`, `erste_spalte_fett`; Zelle `{"ampel": "G", "t": "…"}`; Zeilenhöhe nach Inhalt, ohne `groesse` Schrift automatisch (12 → 9 pt) | echte, editierbare Tabelle |
| `kennzahlen` | Only title | `kacheln` [{`wert`, `label`, `text`, `ampel`, `icon`, `bild`}], `spalten`; `bild` füllt den Rest der Kachel unter dem Text | KPIs |
| `diagramm` | Only title | `art` saeulen/gestapelt/balken/linie/torte, `kategorien`, `reihen` [{name, werte}], `werte_anzeigen`, `fazit` {titel, punkte, icon} | echtes Diagramm (editierbar) |
| `fluss` | Only title | `spalten` [{`titel`, `boxen` [{`titel`, `text`, `klein`, `stil` hell/weiss/dunkel/akzent}]}]; eine Box spannt über alle Zeilen | Datenfluss, Systemlandschaft, Zielbild |
| `bild_text` | Content and image | `bild` (Pfad, relativ zur Spec oder zum Arbeitsordner), `punkte` | Bild + Text |
| `kernaussage` | One content dark | `titel` (Aussage), `text` | Botschaft / Entscheidung |
| `abschluss` | One content dark Outro | `titel` | „Vielen Dank“ |
| `layout` | `layout` (Name aus `bippt layouts`) | `felder` {idx: Text \| [Absätze]}, `bilder` {idx: Pfad} | echte Platzhalter eines Master-Layouts: Two/Three contents, Content and margin, Key message, Bild hochkant |
| `frei` | Only title | `elemente` [{`form`: flaeche/text/linie/icon/punkt/pfeil/karte/band/bild, x, y, w, h …}] in Zoll; `band` mit `label`, `text`, `stil`, `y`, `h`; `bild` mit `datei` (eingepasst, `ausr` l/m/r) | Sonderfälle ohne Code |

## Messen beim Bau
`bippt bauen` schätzt Textbreiten mit den Zeichenbreiten von Boehringer Forward (je Wort und Zeile etwa ±2 %) und bricht
um wie PowerPoint: an Leerzeichen, nach Bindestrich und weichem Trennstrich, vor und nach Gedankenstrich, nicht nach
Schrägstrich. Daraus folgen Warnungen statt stiller Fehler im Render:
- **Titel:** Typen auf „Only title“ beginnen direkt unter der ersten Titelzeile. Braucht der Titel zwei Zeilen (25 pt,
  ab etwa 68–72 Zeichen), warnt `bauen` (und `pruefen`): „Titel braucht 2 Zeilen … ragt in den Inhalt“. bippt rückt den
  Inhalt nicht nach unten – der Titel ist eine Aussage in einer Zeile, Details gehören ins Band oder in den Inhalt.
  Auf „One content“ (`text`, `agenda`) ist Platz für zwei Zeilen; Titel- und Kapitelfolien warnen, wenn der Titel nach
  oben über Logo oder Folienrand wächst.
- **Wortbreite:** Ist ein Wort breiter als sein Textfeld (Karte, Schrittkarte, Tabellenzelle, Box), trennt PowerPoint es
  mitten im Wort. `bauen` nennt die Wörter je Folie; bei `prozess` dazu, wie viele Schritte nebeneinander passen.
  Abhilfe: kürzen, mit Bindestrich trennen (`Projekt-Workshop`), weniger Spalten oder kleinere Schrift.
- **Tabelle:** Zeilenhöhe aus Zeilenumbruch, Schriftgröße und Spaltenbreite. Ohne `groesse` wird die Schrift bis 9 pt
  kleiner, bis alles über Band, Quelle bzw. Fußzeile passt; sonst warnt `bauen` mit Bedarf und Platz in Zoll (bei
  fester `groesse` mit der Größe, die passen würde).
- **Quelle:** Mit `quelle` enden Inhalt und Band über der Quellenzeile (sie wächst bei langem Text nach oben).

## Karten: Hervorhebung und Höhe
`"hervor": true` – Kopfleiste in Accent Green mit dunkelgrüner Schrift (z. B. empfohlene Variante, Zielbild, Argumente).
Nie Akzentgrün als Schrift, Rahmen oder dünne Linie auf Hell. `"hoehe": "inhalt"` (Standard bei `karten`): alle Karten so
hoch wie die vollste; `"voll"`: bis zur Unterkante (Vergleich nebeneinander, Statusfolie).

## Schrittkarten (`prozess`)
`{"ueber": "KW 41", "titel": "Workshop", "punkte": [...], "status": "fertig|aktiv|plan|offen|klaerung|extern|kritisch"}` –
Kopf in Statusfarbe (ohne Status Dark Green), Überzeile klein (Termin, KW, Bedingung), darunter Punkte; Pfeile zwischen
den Köpfen. `kritisch` = Red mit dunkelgrüner Schrift (Eskalation). Ohne `karten` strecken sie sich bis zur Unterkante.
Mit vielen Schritten werden die Spalten schmal (8 Schritte: 1,27 in) – lange Wörter wie „Projektworkshop“ passen dann
nicht mehr; `bauen` warnt und nennt die passende Zahl Schritte (meist höchstens 6).

## Blöcke in Karten (`inhalt` oder Kurzfelder)
`{"punkte": [...]}` · `{"text": "..."}` · `{"phasen": {"namen": [...], "stand": [2,1,0]}}` ·
`{"schritte": [{"status": "fertig|aktiv|offen", "titel", "text"}]}` ·
`{"von_nach": {"von": {"klein", "gross"}, "nach": {...}}}` · `{"kennzahl": {"wert", "label"}}` ·
`{"bild": "pfad.png" | {"datei", "hoehe"}}` (Kartenbreite, Höhe nach Seitenverhältnis, höchstens 2,6 in) ·
`{"hinweis": "..." | {"titel", "text", "strich": true}, "unten": true}`.
Kurzform: `punkte`, `schritte`, `phasen`, `text`, `von_nach`, `bild`, `naechster` (→ Hinweis „Nächster Schritt“ unten), `hinweis`.

## Timeline-Elemente
`{"art": "balken", "von", "bis", "text", "status", "pos"}` · `{"art": "meilenstein", "datum", "text", "status", "pos"}` ·
`{"art": "ueberbrueckung", "von", "bis"}` (rote Linie). `status`: fertig, plan, aktiv, klaerung, offen, extern, kritisch.
Daten: `2026-10-07`, `07.10.2026`, `2026-10` (Monat; bei `bis` = Monatsende), `2026-W43` oder `KW43/2026`.
`pos`: rechts/links/oben/unten – nur nötig, wenn `bauen` „überlappt“ meldet.
`marker` [{datum, text}] = durchgezogene Linie (z. B. Cut-Over); `schatten` [{von, bis, text}] = graue Zone (Feiertage).

## Layout-Kurznamen (`layout`)
titel, titel_dunkel, titel_bild, agenda, kapitel, kapitel_dunkel, inhalt, inhalt_dunkel, zwei_inhalte, drei_inhalte,
inhalt_bild, nur_titel, leer, abschluss, disclaimer, kontakt – oder der exakte Layoutname des Masters.
