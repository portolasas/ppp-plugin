# Folienbibliothek – BI Slide Library

Die offizielle Slide Library (Version 3.3, September 2026, 184 Folien) liegt als `vorlagen/BI_Slide_Library.pptx` im
Plugin. Sie nutzt denselben Master wie die Vorlage. Ihre Folien sind von Designern gestaltet: Spalten mit Kopfboxen,
Icons und Fazit, nummerierte Fakten, Zitate mit Illustration, Bild und Text, Prozesse, Timelines, Porträts, Funnel und
mehr. bippt kopiert sie ins Deck und füllt sie.

## Bildform zuerst
Frag bei jeder Folie zuerst: **Wie würde eine Designerin diese Aussage zeigen?** Erst dann kommt der Text, und er wird kurz:
Zahlen groß, Abläufe als Pfeile, Abwägungen gegenüber, Stimmen als Zitat. Die Bibliothek hat dafür fast immer eine Folie.

| Aussage | Bildform und Folien |
|---|---|
| Eine Botschaft, Position oder Idee | großes Zitat 49 · Idee mit Glühbirne 160–163 · Layout „Key message and image“ (mit Foto) |
| Zahlen, Umfang, Potenzial | nummerierte Fakten 39–44 · Trend 87–91 · Bild mit Kennzahlen 69–70 · Prozentringe 134 · Prozentbalken 132 |
| Problem mit Ursachen und Folge | Bereiche mit Fazit-Band 36–38 · Icons 28 · zwei Texte mit Icon-Band 31–35 |
| Zielbild, Bausteine eines Ganzen | Waben 155–157 · Schnittmenge 153–154 · Zahnräder 165–167 · vernetzte Geräte 158–159 · Pyramide 106 |
| Umfang, Abwägung, Vor- und Nachteile | Pro/Contra 57–58 (Wörter ersetzen: „Im Umfang“, „Nicht enthalten“) · SWOT 56 · Balken mit Pro/Contra 131 |
| alt → neu | Typ `vergleich` |
| Vorgehen, Phasen | Winkelpfeile 78–79 · Kopfbalken 80–81 · Phasen mit Fazit 84 · Icons mit Randspalte 85–86 · sechs Phasen 77 |
| Zeit, Meilensteine | Zeitstrahl 93–96 · Wochenplan 97 · Typ `timeline` für echte Terminpläne |
| Priorisieren, Auswahl | Trichter 171–174 · Wachstum 175 · Kreislauf 92 |
| Rollen, Team, Personen | Organigramm 103–105 · Porträt 107–112 · Tabelle nur im Backup |
| Status, Risiken | Typ `status` mit Ampeln · Statusbericht 59 · Tabelle mit Ampeln 116 |
| Entscheidung, Beschluss, Fazit | Bereiche mit Fazit-Band 36–38 · Management Summary 22 · Typ `kernaussage` |
| Stimmen, Erfahrungen | Zitat mit Illustration 50–54 · drei Zitate 46–48 |
| Bild vorhanden | Bild und Text 62–67 · Collage 71–72 · Gerät 73–75 |
| Zahlenreihen | Diagramme 119–134 mit `daten` · Typ `diagramm` |
| Mehrere gleichrangige Textblöcke, wenn nichts anderes trägt | Layouts „Two contents“, „Three contents“ (Typ `layout`) · Kopfboxen 23–27 |

**Die Form folgt dem Inhalt.** Gleich gebaute Inhalte (parallele Themen, Stränge, Bereiche) bekommen dieselbe Folie; das
gibt dem Deck einen roten Faden. Eine neue Bauart nur, wenn sich die Art der Aussage ändert. Ein gutes Deck hat etwa drei bis
fünf Bauarten, die wiederkehren; Vielfalt um ihrer selbst willen wirkt unruhig.

Texte: 20–40 Wörter auf einer gestalteten Folie, in ganzen Aussagen mit Verb; je Punkt höchstens zwölf Wörter. Die Absätze der
Bibliothek müssen nicht alle gefüllt werden. `bippt bauen` warnt ab drei gleichen Bauarten in Folge, wenn eine Bauart mehr als
die Hälfte der Inhaltsfolien stellt oder mehr als die Hälfte reiner Text ist (das Backup zählt nicht). Ein Deck hat neben Weiß
und Dunkelgrün höchstens eine Akzentfarbe aus den Varianten (Gelb, Blau, Violett, Pfirsich, Grau).

## Bibliothek, Layout oder Generator
- **Bibliothek** (`bib`): alles Gestaltete aus der Tabelle oben.
- **Layout des Masters** (`{"typ": "layout", "layout": "Three contents", "titel": "…", "felder": {"1": […], "16": […], "17": […]}}`):
  echte Platzhalter des Masters, auch Vollbild und Key Message mit Foto (`"bilder": {"10": "foto.jpg"}`). Felder: `bippt layouts`.
- **Generator** (`typ`): Daten mit wechselnder Menge – Status mit Ampeln je Strang, alt → neu, Gantt aus Terminen,
  Maßnahmenliste, lange Tabelle, Fluss.
- Titelfolie: Typ `titel`; Bibliothek 177–179 nur für interne Marken mit Wortmarke.

## Ablauf
1. Storyboard: je Folie Aussage, Bildform und Folie aus der Tabelle oben bzw. der Übersicht unten (Zahl der Bereiche, Bild
   ja/nein, hell/dunkel). Gleich gebaute Inhalte bekommen dieselbe Folie.
2. `bippt katalog --folien n,m` für die gewählten Folien → je Form id, Art, Lage, Schrift, Platz (Zeilen × Zeichen) und Beispieltext. Die
   ids gelten für jede Kopie der Folie.
3. In der Spec: `{"bib": n, "titel": "…", "texte": {"<id>": "Text", "<id>": ["Absatz", "Absatz"]}, "bilder": {"<id>": "foto.jpg"},
   "daten": {"<id>": {"kategorien": […], "reihen": [{"name": "…", "werte": […]}], "titel": "…"}},
   "tabellen": {"<id>": [["Kopf", "…"], ["Zelle", "…"]]}, "entfernen": [<id>]}`, dazu wie bei Basisfolien `ersetzen`,
   `aendern`, `elemente`, `notizen`, `ausblenden`.
   - `texte`: eine Zeichenkette oder eine Liste von Absätzen. Der n-te Absatz bekommt das Format des n-ten Absatzes
     der Bibliothek – der Katalog nennt es („Absätze: fett, Text, 2× Punkt“). Mehr Absätze als vorher übernehmen das
     Format des letzten; ein anderes Format mit `{"t": "12 Wochen", "wie": 5}` (Format von Absatz 5). `**fett**` wie
     überall.
   - **Jeden Blindtext ersetzen oder seine Form entfernen** – auch Überschriften wie „Header box“, „Headline“, Zahlen
     wie „20XX“ und gelbe Hinweisetiketten („Excel based chart“, „PowerPoint Master available …“).
   - **Icons ersetzen, nicht entfernen.** Die Beispiel-Icons (Diagramm, Hund, Pflanze, Lupe, Euro-Münze, Tablette) gegen
     passende Brand-Icons tauschen: `"bilder": {"<id>": "icon:calendar"}`; Namen liefert `bippt icons <englischer Begriff>`
     (895 Icons), die Variante wählt bippt nach dem Untergrund (`icon:calendar:white` erzwingt sie). Winkel in 36–38, Plus und
     Minus in 57–58 passen fast immer und bleiben.
   - **Illustrationen bleiben,** wenn sie den Inhalt nicht stören (Reagenzglas, Hände, Glühbirne, Laborkraft): Sie tragen die
     Folie, ohne sie entsteht ein Loch. Ein Tier nur beim passenden Thema; sonst eine andere Folie wählen. „Logo (nicht
     ändern)“ bleibt.
   - Folien ohne Titelzeile (49–54, 57–58, 65–67, 69, 160–163): Kernaussage über `texte`.
   - `tabellen`: Zeilen mit Kopfzeile; `null` lässt eine Zelle stehen. Mehr Zeilen kopieren die letzte, weniger
     Zeilen oder Spalten fallen weg (die Tabelle behält ihre Breite).
   - Bilder nur mit genug Auflösung (mindestens 150 dpi im Rahmen: Rahmenbreite in Zoll × 150 Pixel). Der
     Bildplatzhalter beschneidet; mit `{"datei": …, "ausschnitt": "oben"}` den Ausschnitt wählen.
4. `bippt bauen`: Es warnt bei Text, der nicht in seine Form passt, bei halb leeren Flächen, übrigem Blindtext und zu
   Eintönigkeit. Alles beheben, bevor das Deck rausgeht.

Platz: Die Angabe im Katalog ist eine Obergrenze. Für ein ruhiges Bild die Hälfte bis zwei Drittel nutzen –
Kopfboxen eine Zeile, Spaltentexte 2–4 kurze Punkte, Fakten ein Satz.

## Übersicht (Folie: Inhalt)
Grundlagen der Bibliothek (1–5, Kapiteltrenner 3, 6, 14, 21, 55, 61, 76, 102, 113, 118, 135, 152, 164, 176, 180) sind
Beispiele; die Kapiteltrenner taugen mit neuem Titel als schlichte Kapitelfolie (grün).

**Agenda**
- 7 nummerierte Liste (bis 8 Punkte) · 8 Kacheln hell mit Seitenzahl (bis 15) · 9 dasselbe dunkel
- 10 große Nummern 01–08 auf Dunkelgrün · 11 nummerierte Blöcke 01–09 mit Kalender-Illustration, dunkel
- 12 Tagesordnung mit Uhrzeiten (`tabellen`) · 13 dasselbe mit Tag-Reiter

**Kapitel**
- 15–18 Kapitel mit Illustration: Hand mit Münze (grün), Hand mit Kugel (dunkel), Auge (Pfirsich), Megafon (Gelb)
- 19–20 Abschnitt mit Illustration: Hunde (Violett), Team (Blau)

**Text und Layout**
- 22 Management Summary: Aufzählung mit Hervorhebungen und dunkler Takeaway-Box
- 23–26 Spalten mit dunkler Kopfbox: 1, 2, 3, 4 Spalten (in 26 die vierte hervorgehoben) · 27 zwei Zeilen
- 28 drei Spalten mit Icon, mittlere hervorgehoben · 29 drei Spalten mit Illustration
- 30 fünf Punkte mit Icon und dunkler Randspalte für die Kernaussage
- 31–35 zwei Textspalten oben, Band mit fünf Icons unten (Dunkelgrün, Pfirsich, Blau, Gelb, Violett)
- 36–38 drei Bereiche oben, Fazit-Band mit drei Punkten unten (Dunkelgrün, Gelb, Blau)
- 39–44 drei nummerierte Fakten 01–03 mit Reagenzglas (Weiß, Pfirsich, Blau, Gelb, Violett, Grau)
- 45 acht kleine Textboxen, eine hervorgehoben
- 46–48 drei Zitate (dunkel, hell, farbige Kästen) · 49 ein großes Zitat auf Dunkelgrün
- 50–54 Zitat mit Illustration: Laborkraft (Pfirsich), Ärzte (Blau), Forscherin (Gelb), Produktion (Violett), Team (Grau)

**Beziehung und Vergleich**
- 56 SWOT mit Glühbirne · 57–58 Pro und Contra (dunkel bzw. Violett rechts)
- 59 Statusbericht: vier Punkte mit Ampel und Zahnrad · 60 Projektbeispiel mit Punktbewertung

**Bilder**
- 62–64 Bild rechts hochkant, Text links (64 Pfirsich mit Icon) · 65–67 Bild oben, Titel und Text unten (dunkel,
  Grau, Blau) · 68 vier Textboxen mit Bild · 69–70 Bild oben, vier Kennzahlen unten (dunkel, hell)
- 71 drei Bilder mit Text · 72 Bildcollage mit Kennzahl · 73 Laptop · 74 Tablet · 75 Smartphone (Bildschirmfotos)

**Prozesse, Phasen, Zeit**
- 77 sechs Phasen an einem Pfeil, Texte abwechselnd oben und unten
- 78–79 drei Phasen als Winkelpfeile mit Überschrift und Punkten (letzte dunkel bzw. Blau)
- 80 drei Phasen mit Kopfbalken · 81 vier Phasen mit Kopfbalken und Dauer („XX weeks“)
- 82 drei, 83 vier Phasen mit Linie · 84 vier Phasen mit dunklem Fazit-Band
- 85–86 vier Phasen mit Icons und Randspalte (dunkel, Gelb)
- 87–91 Trend mit Kennzahlen („+33.100“, „-25.000“) und Erläuterung · 92 Kreislauf mit drei Segmenten
- 93–94 Zeitstrahl mit sechs Zeitpunkten und Icons (einer hervorgehoben) · 95 fünf Zeitpunkte · 96 sechs Zeitpunkte
  im Zickzack mit Illustrationen · 97 Wochenplan Mo–So
- 98–101 Projektplan als Tabelle (Jahr in Quartalen, Quartal in Wochen, 1 bzw. 2 Jahre in Monaten) – Balken liegen frei
  auf der Tabelle; für echte Termine Typ `timeline`

**Organisation und Personen**
- 103–104 Organigramm mit drei Ebenen (hell bzw. dunkel) · 105 mit Fotos · 106 Pyramide mit Text
- 107–108 Porträt mit Foto und Kontakt (hell, dunkel) · 109 Porträt mit Illustration · 110–111 Profil mit vier
  Textblöcken · 112 Bild, Team und Projektbeschreibung

**Tabellen** (`tabellen`; lange oder wachsende Tabellen besser mit Typ `tabelle`, der die Schrift anpasst)
- 114–115 Zahlentabellen mit Summenzeile · 116 Tabelle mit Ampeln (Ampelpunkte sind Formen neben der Tabelle)
- 117 Angebotsvergleich mit Randspalte

**Diagramme** (`daten`; Diagrammtitel mit `"titel"` setzen oder `""` für keinen)
- 119 Säulen · 120 Säulen mit Linie · 121 Balken · 122 Balken 100 % gestapelt · 123 Linien · 124 Netz mit Randspalte
- 125 Blasen (nicht über `daten`) · 126 Torte · 127 Ring · 128 zwei Ringe mit Text · 129 Gesamtbudget als Ring
- 130 Linie mit Bewertungstabelle · 131 Balken mit Pro/Contra · 132 drei Prozentbalken · 133 Umfrage · 134 Fakten
  als Prozentringe (132–134: Hinweisetikett „Excel based chart“ entfernen)

**Karten** – 136 Welt, 137–138 Europa, 139 Deutschland, 140–141 USA, 142 Südamerika, 143 Brasilien, 144–145 Kanada,
146 Mexiko und Mittelamerika, 147 Japan, 148 TCM, 149 IMETA, 150 ASKAN, 151 RCV; Länder einfärben über `aendern`
ist aufwendig – meist mit Text und Markierung (`elemente`) arbeiten.

**Statische Elemente**
- 153 Schnittmenge zweier, 154 dreier Kreise · 155–157 Waben mit Text (dunkel, hell, Blau)
- 158–159 vernetzte Geräte · 160–163 Idee mit Glühbirne (dunkel, Gelb, Violett, Grau)

**Dynamische Elemente**
- 165–167 Zahnräder mit drei Texten · 168–170 Wortwolke · 171–174 Trichter (Funnel) mit vier Stufen · 175 Wachstum in
  drei Stufen

**Abschluss**
- 181 Rechtshinweis · 182–183 „Thank you!“ (183 mit Illustration) · 184 Kontakt mit Bild
