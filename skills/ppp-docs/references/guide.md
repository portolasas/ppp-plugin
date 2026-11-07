# ppp guide

`ppp guide docs/handbook/<name>.md` writes the handbook as `docs/handbook/<name>.docx`. The rules for its chapters are in SKILL.md; the walks and their pictures in ppp-app-walk.

## What it reads
- Headings, paragraphs, lists and tables of the Markdown.
- `<!-- walk: <name> -->` on its own line: the numbered `text` of `docs/handbook/walks/<name>.json`, its pictures with caption and the legend of the frames.
- `<!-- toc -->`: a table of contents that Word fills on F9. `<!-- pagebreak -->`: a new page.
- `> text`: a shaded box for a note or caution. `- [ ] text`: a box to tick.
- `<!-- for: … -->`, `<!-- kind: … -->`, `<!-- avoid: … -->` and `<!-- solution -->`: SKILL.md, steps 2 and 4.

## Layout
A step, its picture, caption and one-line legend stay on one page; a picture takes at most half the page height. Table heads repeat, tables up to 15 rows stay on one page, and a blank paragraph keeps two tables apart, because Word joins tables that touch when it saves [B]. `--orientation portrait|landscape` turns every section whatever the template has; portrait suits step-by-step guides with screenshots, about two steps with picture per page.

## Options
- `--word` then opens the file in Microsoft Word, updates table of contents and fields, saves it and prints its pages, so nobody presses F9. On macOS through Launch Services, because Word's sandbox refuses an AppleScript open [B]; on Windows through COM with the file in `PPP_WORD_FILE`, because `powershell -Command` passes no arguments to `$args` and Word got no file [B] (user, 2026-11-05).
- `--role <role>` takes only the sections marked for that role, `--kind quick|exercises` the quick guide or the exercise sheet. The default file is `<name>[-<kind>][-<role>].docx`.
- `--kind deck --role <role>`: the role's training deck, [deck.md](deck.md).
- `ppp guide <walk> [<walk> ...] --title "<title>"` builds a guide of walks alone, one chapter per walk, as `docs/handbook/<first walk>.docx`. With `--role "<name>"` it builds the guide of one role from the given walks, `docs/handbook/<first walk>-<role>.docx`, and names the role under each chapter title; it refuses pictures from a run that did not finish or is not proven as that role.
- `--out` sets the file, `--template` a Word template whose styles apply.

Warnings: more than three clicks in a row without a text, words of `<!-- avoid: … -->`, a quick guide above about one page. A note: a walk of another role in a role's handbook.

## Template and fonts
- `ppp guide` sets the document title and turns `STYLEREF "Title"` in headers and footers into a `TITLE` field that shows it: German Word looked for a style "Titel" and printed an error in the footer [B] (GEN-20261104-WIN-02).
- If bi-designer is installed, copy the Word template its `office.md` names to `docs/handbook/template.docx` and pass that, and set `markColor` of the walks to a brand colour from its tokens that stands out from the app. Without bi-designer the neutral look stays.
- Word knows fonts installed while it runs only after a restart. Word for Mac's own PDF export may replace a corporate font, so judge the font in Word itself [B] (GEN-20261104-MAC-01).
