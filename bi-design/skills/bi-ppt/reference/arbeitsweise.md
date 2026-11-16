# Arbeitsweise – Storyline, Texte und Gestaltung

Abgeleitet aus dem CPV-Projektteam-Update (24.09.2026) und dem Steering-Committee-Update (07.10.2026), beide vom Nutzer
abgenommen, und den How-to slides des BI-Masters v2.1. **Der Master geht vor:** Wo ein Referenzdeck vom Master abweicht
(z. B. aufgehellte Farben), gilt der Master. Anonymisierte Muster: [../beispiele/projektteam.spec.json](../beispiele/projektteam.spec.json)
(Projektteam) und [../beispiele/beispiel.spec.json](../beispiele/beispiel.spec.json) (Steering, alle Typen).

## Regeln des Masters (How-to slides, BI-Master v2.1)
- **Farben:** nur „Theme Colors“ und „Custom Colors“ des Masters. Keine Abstufungen unter den Designfarben (heller/dunkler
  x %) und keine Standardfarben – sie sind „not CD-compliant“. `bippt pruefen` meldet beides als FEHLER.
- **Ampel:** Signal Green/Yellow/Red (Custom Colors), immer mit Legende; Zwischenstand Gelb–Rot als `YR`.
- **Diagramme:** automatische Farbfolge des Masters = Designfarben Akzent 1–6 (Dark Green, Accent Green, Violet,
  Yellow, Red, Blue); Linien auf Weiß nur in dunklen Farben.
- **Fußzeile:** `<Präsentationstitel>     |     ONLY FOR INTERNAL USE` (zentral für alle Folien); Titelfolie nur der
  Vermerk. `fusszeile` = Präsentationstitel, z. B. „Projekt | Projektteam-Update“; den Vermerk nie weglassen.
- **Titelfolie:** Titel in 1–2 Zeilen, optional Untertitel, dann „Autor | Datum | Ort“ (Ort darf fehlen).
- **Textebenen** im Inhaltsplatzhalter: Ebenen 1–4 16 pt, ab Ebene 5 12 pt. In Karten, Tabellen und Grafiken 10–12 pt,
  nie unter 9 pt (Überzeilen, Legenden 8,5–9 pt).
- Layouts und Platzhalter aus dem Master, Logo kommt aus dem Master, Bilder nur über Bildplatzhalter.

## Publikum → Umfang und Dichte
| Publikum | Sichtbare Folien | Wörter je Folie (`pruefen --woerter`) | Schwerpunkt | Backup |
|---|---|---|---|---|
| Steering Committee / Management | 6–9 | ≤ 120 | Status, Änderungen, Entscheidungsbedarf, Timelines, nächste Schritte | Detailfolien ausgeblendet |
| Projektteam | 8–12 | ≤ 200 | Arbeitsstand je Strang, Vorgehen, Abhängigkeiten, Termine | Kontext, Mengengerüst, Zielbild, Rollen |
| Sounding Board / Fachgremium | 5–8 | ≤ 150 | Lösungsidee, Varianten, Bitte um Feedback | Varianten-Details |
| Onboarding / Info | frei | ≤ 150 | Erklären, Kontext, Kontakte | – |

## Standard-Storyline Projektteam-Update
1. `titel` – Projekt, Anlass, Autor | Datum
2. `agenda` – Stränge in der Reihenfolge der Folien, dazu Timelines, Nächste Schritte, Änderungen
3. `status` – „Wo stehen wir?“: je Strang Ampel, Phasen, 2–3 Fakten, nächster Schritt; Band `akzent` mit der Gesamtaussage
4. Je Strang 1–2 Folien, kritischer Strang zuerst:
   - Entscheidungsbedarf → `karten` mit `kopf` „Zu entscheiden (wer):“ + Ja/Nein-Frage, Varianten als Karten
     (empfohlene mit `hervor`), Band „Unsere Position:“;
   - Vorgehen, Eskalationslogik → `prozess` mit Schrittkarten (`ueber` = Termin, `punkte`), darunter Argumente / Risiken;
   - Umstellung alt → neu → `karten` mit `von_nach` und Punkten „Stand und nächste Schritte“.
5. `timeline` in Kalenderwochen für den kritischen Pfad (Feiertage als `schatten`, Cut-Over als `marker`, Boxen
   „Taktgeber …“ und „Zum Vergleich …“)
6. `vergleich` – „Was hat sich seit dem letzten Update (TT.MM.) geändert?“ inkl. Zeilen Projektende und Ampel; Band
   „Kernänderung:“ (`hell`)
7. `massnahmen` – „Nächste Schritte und Termine“ (Wann | Was | Worum es geht), chronologisch; Band „Kritischer Pfad:“
8. `timeline` „Gesamtüberblick“ über alle Stränge (ab 18 Monaten Quartale) mit Key Facts
9. Backup (`ab_hier_ausblenden`): Mengengerüst (`tabelle`), Zielbild (`fluss`), „Was ist passiert?“ (`karten`), Rollen (`tabelle`)

## Standard-Storyline Steering-Update
`titel` → `status` (+ Band) → `vergleich` (bei Folge-Updates) → 1–2 Strangfolien nur zu strategisch Relevantem →
`timeline` Gesamtüberblick (+ KW-Timeline bei kritischem Pfad) → `massnahmen` + „Kritischer Pfad“ →
Entscheidungsbedarf nur, wenn wirklich nötig (`kernaussage` oder Band) → `kapitel` „Backup“ + Detailfolien der Basis.

## Texte – so schreiben
- **Aktionstitel:** Der Titel ist die Aussage, nicht das Thema. Strangfolien beginnen mit dem Strang:
  „Strang A – Die Freigabe des Zugriffswegs ist der kritische Pfad“, nicht „Strang A – Zugriffsweg“. Fragen nur als
  Orientierung auf Status- und Änderungsfolie („Wo stehen wir?“, „Was hat sich … geändert?“). Eine Zeile: auf
  Inhaltsfolien höchstens etwa 68 Zeichen (25 pt) – der Inhalt beginnt direkt darunter; `bippt bauen` warnt bei zwei Zeilen.
- **Punkte sind ganze Aussagen** mit Subjekt und Verb, konkret: wer, was, bis wann, wie viel („Partner beauftragt,
  Kick-off erfolgt, Workshop KW 41“; „~10 Kampagnen bis zum Systemwechsel“). Keine Schlagworte ohne Aussage.
- **Folge mit Gedankenstrich:** Fakt – Konsequenz („Go-Live Ende 01/2027 – Überbrückung ca. 4 Wochen, innerhalb des
  tolerierbaren Fensters“). So trägt jeder Punkt seine Bewertung.
- **Je Strang auf der Statusfolie:** 1. was erreicht wurde, 2. was sich geändert hat oder hakt, 3. ggf. Bewertung;
  „Nächster Schritt“ immer mit Termin oder KW und Beteiligten.
- **Varianten gleich gliedern:** Was ist es, Stand der Freigabe, Validierungsaufwand, Go-Live und Folge, Risiko –
  in derselben Reihenfolge, damit man Zeile für Zeile vergleichen kann; Empfehlung im Kartentitel „(Empfehlung)“.
- **Bänder mit festem Label:** „Zu entscheiden (wer):“, „Unsere Position:“, „Kernänderung:“, „Kritischer Pfad:“,
  „Taktgeber ist …“, „Status von Gelb wieder auf Grün:“, „Entscheidung:“, „Schlussfolgerung:“. Höchstens zwei Zeilen.
- **Zeitbezug:** „jede Woche Verzug verschiebt den Go-Live 1:1“ – Abhängigkeiten in Wochen oder Monaten beziffern.
- **Termine:** TT.MM.JJJJ, Wochentag bei Sitzungen („Di, 29.09.2026“), Monate „10/2026“, Spannen „03–04/2027“ mit
  Halbgeviertstrich, Kalenderwochen „KW 41“. Status in Balken: „geliefert ✓“, „läuft“.
- **Namen:** Initial + Nachname („M. Muster“), Partner beim Firmennamen; volle Namen nur in Rollen-Tabellen im Backup.
- **Änderungen ggü. Vorversion** immer zeigen (Vergleich oder Band), nie still aktualisieren.
- **Nicht überladen:** ≤ 5 Punkte je Karte, ≤ 2 Zeilen je Punkt; Wortgrenze je Publikum (oben); Rest ins Backup.

## Gestaltung
- **Gestaltete Folie vor generierter:** Agenda, Kapitel, Bereiche mit Kopf oder Icon, Fakten, Zitate, Bild und Text,
  Phasen, Team und Abschluss aus der Folienbibliothek ([bibliothek.md](bibliothek.md)); generiert wird, was Daten mit
  wechselnder Menge zeigt.
- **Grafik vor Text:** Abläufe → `prozess` oder Bibliothek 77–86, Termine → `timeline`, alt/neu → `vergleich`, Zahlen →
  `kennzahlen`/`diagramm` oder Bibliothek 39–44, 69–70, 87–91, Systeme und Datenwege → `fluss`.
- **Eine Kernaussage je Folie** als `band`: `dunkel` (Position, Entscheidung), `akzent` (Gesamtaussage der Statusfolie),
  `hell` (Kernänderung, kritischer Pfad, Fazit, Sonderfall).
- **Hervorheben** nur über Fläche Accent Green mit dunkelgrüner Schrift (`hervor`), nie Akzentgrün als Schrift, Linie oder
  Rahmen auf Hell.
- Karten in Inhaltshöhe (`karten`), volle Höhe nur, wenn Karten nebeneinander verglichen werden (`"hoehe": "voll"`).

## Neue Version einer bestehenden Präsentation (Modus V)
1. Folienbeschreibung `alt.md` lesen → Folienliste mit Nummern, Inhalt und Gestaltung (ohne sie: `bippt beschreiben alt.pptx`).
2. Je Folie entscheiden: behalten (ggf. `ersetzen`), ausblenden (Backup), entfernen, oder durch neuen Typ ersetzen.
3. Veraltete Aussagen in behaltenen Folien über `ersetzen` korrigieren (exakter Textausschnitt aus `analyse`; die
   Formatierung außerhalb des Treffers bleibt). `bippt bauen` warnt, wenn eine Ersetzung nicht gefunden wurde.
4. Mehr als Text tauschen (Bild im Bildplatzhalter, Absätze ergänzen, Läufe im Band, Formen verschieben, entfernen):
   `bippt analyse alt.pptx --formen --folien n` nennt id, Name und Läufe je Form der betroffenen Folien; dann `aendern` und `elemente` an der Basisfolie
   ([folientypen.md](folientypen.md) › Basisfolien). Kein eigenes python-pptx-Skript.
5. Titelfolie: `{"basis": 1, "platzhalter": {"1": ["Neuer Anlass", "Name | Datum"]}}`.
6. Basisfolien mit Abstufungen oder fremden Farben: `farben_angleichen` und im Render prüfen.

## Effizienz
- Quellen einmal lesen (`bippt lesen -o _quellen.md`), danach nur gezielt nachschlagen. Bestehende Decks über ihre
  Folienbeschreibung, einzelne Folien mit `--folien`.
- Erst komplette Spec, dann bauen – nicht Folie für Folie rendern.
- Render: Kontaktbogen (80 dpi) reicht für die Übersicht; Einzelfolien nur bei Auffälligkeiten (`--folien 3,6 --dpi 110`).
- Korrekturschleifen ≤ 3; was danach offen ist, im Abschluss nennen.
