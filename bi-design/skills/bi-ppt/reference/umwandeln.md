# Umwandeln – fremdes Design → BI-Design

## Entscheiden (eine Frage, Empfehlung zuerst)
| Weg | Wann | Ergebnis |
|---|---|---|
| **In die Marke übertragen (Empfehlung)** | Deck ist gut gestaltet, z. B. aus der Erstellen-Funktion von Copilot | Gestaltung und Inhalt bleiben; Farben, Schriften, Icons, Logo und Fußzeile der Marke |
| **Neu bauen** | Inhalt muss verdichtet werden oder Folien sollen BI-Layouts nutzen | 100 % BI-Master, Inhalte verdichtet |
| **Stil angleichen** | sehr viele Folien, komplexe Grafiken/Bilder, schnell gebraucht | Farben/Schriften BI, alter Master bleibt (Befund) |
| Kombination | Kernfolien neu, Detail-/Bildfolien als Stil-Kopie | zwei Dateien, Nutzer fügt zusammen |

## In die Marke übertragen
Entscheidung des Nutzers (30.10.2026): Das Deck muss nicht in die Layouts des Masters passen, wenn die Elemente markenkonform sind.
Die Erstellen-Funktion von Copilot gestaltet in HTML und übersetzt das in PowerPoint-Formen; das Ergebnis ist oft besser als alles, was
wir bauen. Darum nehmen wir es als Quelle.
1. `bippt umwandeln marke fremd.pptx -o ziel.pptx`. Bekannte Icon-Formen des Designers tauscht bippt selbst (`tools/bippt/designer_icons.py`). Nur unbekannte stehen
   unter OFFENE ICONS, mit Schlüssel und Text daneben; `<Ziel>_icons_offen.png` zeigt die Formen. Keine offenen: weiter mit Schritt 3.
2. Je Schlüssel nach der Form ein Brand-Icon wählen, das sie zeigt (Liste `marken/boehringer-ingelheim/icons.txt`, oder `bippt icons <englischer Begriff>`), und in eine
   JSON-Datei schreiben: `{"ccf86a": "bar-chart-trend-up"}`. Soll dasselbe Icon auf einer Folie anders sein: `{"2": {"7": "clock"}}`. Dann erneut mit `--icons icons.json`.
   Fertig bei „0 nur umgefärbt“ und ohne Warnung „Einförmig“. Häkchen und Punkte vor Listen zählen nicht. Neue Formen gehören danach in die Tabelle.
3. `bippt pruefen` und `bippt sichten`. Überlappung und Überstand beheben. Leere nur nennen: Die Gestaltung stammt vom Designer.
4. Inhalt nicht ändern und nicht kürzen. Fotos färbt bippt nicht um; es meldet sie.

Was der Befehl macht:
- **Farben nach Rolle.** Die dunkle Hausfarbe wird Dark Green, die häufigste andere Farbgruppe Accent Green, die übrigen Medium und Dark Blue;
  helle Flächen Warm und Light Gray, gedämpfter Text Gray 7. Diagramme und Tortengrafiken nehmen die Chart order, damit Kategorien
  unterscheidbar bleiben. Signalfarben nur, wenn das Deck Rot und Grün hat: Orange ist kein Alarm.
- **Fotos** bleiben. Fotos und Flächen über die ganze Folienhöhe enden über dem Logo; Fotos werden dafür beschnitten, nicht verzerrt.
- **Einpassen.** Was in Logo oder Fußzeile ragt, wird in der Höhe eingepasst: Karten werden flacher, ihr Inhalt behält die Größe. Stand- und
  Quellenzeilen wandern zwischen Logo und Fußzeile.
- **Weg fallen** Vollbilder, Farbschleier über Fotos, ganz durchsichtige Bilder, Fußtexte und Seitenzahlen des Designers, runde Ecken und Schatten.
- **Schrift:** 9 pt, wo es ohne neue Zeile geht, und dann für alle gleich großen Texte der Folie.
- Die Titelfolie kommt aus dem Master. Ein leeres Element bleibt leer: Fehlt schon im Original etwas (eine Karte ohne Bild), im Abschluss nennen.

## Weg 1 – Neu bauen
1. `bippt analyse fremd.pptx` (Überblick) und `bippt pruefen fremd.pptx` (Ausgangsbefunde, für den Abschluss).
2. `bippt umwandeln entwurf fremd.pptx [-o ziel.spec.json]` → `fremd_BI.spec.json` (+ `fremd_medien/` mit Bildern
   neben der Spec; verknüpfte Bilder werden nicht übernommen).
   Der Entwurf ordnet zu: Titel → `titel`, Diagramm → `diagramm` (Daten übernommen), Tabelle → `tabelle`,
   Bild+Text → `bild_text`, 2–4 Textblöcke → `karten`, sonst `text`. Originalnotizen bleiben.
3. Spec verdichten (das ist die eigentliche Arbeit): Aktionstitel, passende Typen (Abläufe → `prozess`, Termine →
   `timeline`, alt/neu → `vergleich`, Zahlen → `kennzahlen`), Band je Folie, Felder `_quelle_folie`/`_hinweis` löschen.
   Inhaltlich nichts erfinden – Unklares fragen (fragen.md, Modus U).
4. `bippt bauen` → `pruefen` → `rendern` wie üblich. Abschluss: Folienzuordnung alt → neu als Tabelle.

## Weg 2 – Stil angleichen
`bippt umwandeln stil fremd.pptx [-o ziel.pptx]` – ersetzt jede Nicht-Markenfarbe durch die nächste Markenfarbe
(Helligkeit gewichtet), setzt fremde Schriften auf die Theme-Schriften und übernimmt Farb- und Schriftschema des
BI-Masters ins Theme. Danach `pruefen` und `rendern`: auf Kontrast (Akzentgrün auf Hell!) und kaputte Grafiken prüfen.
Grenzen: Layouts, Logo und Hintergrundbilder des alten Masters bleiben; Bilder werden nicht umgefärbt.
