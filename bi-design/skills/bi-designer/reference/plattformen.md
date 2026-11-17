# Other platforms

Legend: [B] confirmed · [O] open · [V] version-dependent

## Power BI
- Import the ready theme: [../marken/boehringer-ingelheim/powerbi-theme.json](../marken/boehringer-ingelheim/powerbi-theme.json)
  (View › Themes › Browse for themes). Data colors follow the chart order; fonts Segoe UI.
- Titles Dark Green; avoid Accent Green lines on white backgrounds for thin elements (low contrast) –
  use it as fill for large bars or on Dark Green.
- Logo: Dark Green logo top left/right on white report background (SVG/PNG via Image visual).
- One surface per report, on every page and in every visual: **white** (default: page and boxes White, text Dark
  Green) or **Dark Green** (page and boxes Dark Green, text White, highlight Accent Green). On Dark Green the chart
  colours are the ones with at least 4.4:1 there: Accent Green, Medium Blue, Medium Yellow, Red, Medium Violet,
  Dark Yellow, White.
- Colours with a meaning (phases, products, reasons) are brand tokens, from the chart order first, the same token in
  every visual; a colour measure for conditional formatting returns token hex values.

## Code apps / web (React, HTML, Markdown exports)
- Generate CSS from tokens:
```css
@font-face { font-family: "Boehringer Forward Head"; src: url("./fonts/BoehringerForwardHead-Bd.woff2") format("woff2"); font-weight: 700; font-display: swap; }
@font-face { font-family: "Boehringer Forward Head"; src: url("./fonts/BoehringerForwardHead-Md.woff2") format("woff2"); font-weight: 500; font-display: swap; }
@font-face { font-family: "Boehringer Forward Text"; src: url("./fonts/BoehringerForwardText.woff2") format("woff2"); font-weight: 400; font-display: swap; }
@font-face { font-family: "Boehringer Forward Text"; src: url("./fonts/BoehringerForwardText-Bd.woff2") format("woff2"); font-weight: 700; font-display: swap; }
:root {
  --bi-dark-green: #08312A; --bi-accent-green: #00E47C; --bi-white: #FFFFFF;
  --bi-light-gray: #F6F5F3; --bi-warm-gray: #E5E3DE; --bi-black: #000000;
  --bi-dark-blue: #076D7E; --bi-light-blue: #D2F2F7; --bi-medium-yellow: #FFD03D;
  --bi-dark-red: #86251B; --bi-light-red: #F5CDB9; --bi-dark-violet: #5D4495; --bi-light-violet: #E0E1F6;
  --bi-gray-5: #B7B6B2; --bi-gray-7: #5C5B59;
  --bi-signal-green: #1EAD1B; --bi-signal-yellow: #FF8413; --bi-signal-red: #F62B2B;
  --bi-font-head: "Boehringer Forward Head", "Segoe UI", sans-serif;
  --bi-font-text: "Boehringer Forward Text", "Segoe UI", sans-serif;
  --bi-radius: 0px;
}
```
- Font files only inside the company solution (licensed brand asset), never in public repositories.
- Logo as inline SVG or `<img>` with the correct variant; favicon from the symbol.

## HTML mail (Outlook, Power Automate „Send an email“)
- Table layout, width 600 px, **inline styles only** (no `<style>` blocks, no web fonts):
  `font-family: 'Segoe UI', Arial, sans-serif; color: #08312A;`
- Header row `bgcolor="#08312A"` with White text and the White/Accent Green logo as hosted PNG (a URL the
  recipients can read; no Base64 – Outlook blocks it), `alt` text set.
- Button: `<a href="…" style="background:#08312A;color:#FFFFFF;padding:10px 16px;text-decoration:none;display:inline-block;">`.
- Status boxes with the role pairs (fill + text) from MARKE.md; footer Light Gray, small Dark Green text.

## Teams Adaptive Cards
- Cards cannot use custom hex colors; only host styles (`default`, `accent`, `good`, `warning`,
  `attention`, `emphasis`). Map: good = success, attention = error, warning = warning, accent = info. [B – schema limit]
- Branding in cards only via a small logo/icon image; the image URL must be reachable for the card
  client (e.g. a SharePoint library the users can read) [O]. Keep cards otherwise neutral.

## Model-driven apps
- Header/theme colors via the app's modern theming or classic theme record: header Dark Green,
  accent Accent Green, navigation text White [O][V]. Logo: symbol or white logo on the header.

## Documents (HANDBUCH, TECHNIK as HTML/PDF export)
- Headings Dark Green, accent lines Accent Green on Dark Green bands only, body Black/Dark Green,
  Light Gray info boxes. Markdown itself stays unstyled.
