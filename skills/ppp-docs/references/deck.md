# Training deck

`ppp guide docs/handbook/<name>.md --role <role> --kind deck [--title "<app>"] [--out docs/training/<file>.pptx]` builds one compact deck per role in the corporate design of bi-design (BI-Master), from the same Markdown and pictures as the handbook, so a change of the handbook reaches Word and slides alike. Without bi-design the command writes the spec only, and bi-ppt builds it. It finds bippt in the installed plugins or a clone of bi-design beside ppp; `--bippt <path to bippt.py>` names it, `--bippt -` writes the spec only.

## Parts
- Title and agenda; per handbook chapter a divider and per section one slide; the quick guide as a chapter; the exercises, their solutions on hidden slides at the end.
- A task with a walk gives one slide with the walk picture that has the most labelled marks, uncropped, what the role sees differently below it. Beside it the lead-ins (**What for:**, **You need:**), the caption as head, picture text, the legend as numbered badges and the result in a box, as much as fits; a caution box becomes the band.
- All step texts, help lists and what did not fit go into the speaker notes, for the trainer.
- A table of roles gives one card per role with the reader's own highlighted, other tables a table slide. A list of three gives a designed slide with icons, two or four rows across the slide with large icons, more a text slide. An exercise gives three rows with the task highlighted.

## Content
A deck teaches what the tool needs, not what the users know from their trade: skip sections such as shift times or plant basics with `<!-- deck: skip -->`, and make sure what users must judge in the tool has a section of its own, for example how sure a forecast is.

## Lines below a heading
After `<!-- for: … -->`, ignored by Word:
- `<!-- deck: skip -->`
- `<!-- deck: title <statement> -->`, `{role}` for the role
- `<!-- deck: heads <a> | <b> -->` and `<!-- deck: icons <a>, <b> -->` for list items; icon names from `bippt icons <term>`
- `<!-- deck: steps -->`: a list as process
- `<!-- deck: tiles -->` with `<!-- deck: ampel G, -, Y, R -->`: a small table as coloured tiles, `-` keeps the neutral bar; with a caution box the section's paragraphs stand below the tiles
- `<!-- deck: shot <picture id> -->`

## Check
Render with `bippt rendern <deck> --alle` and look at every slide: text hidden under the band still shows in the PDF text, so only the picture counts [B] (GEN-20261105-WIN-05). Fix in the Markdown or the deck lines, never in PowerPoint, and delete the `_render_*` folders. Build commands go into `docs/handbook/README.md`.
