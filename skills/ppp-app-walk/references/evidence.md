# Evidence of ppp walk

Status: **[B]** observed in the tenant, **[O]** open. On a surprise write a lesson that names the line it confirms or contradicts.

## What ppp walk handles by itself
Behaviour the tool already has, with the observation behind it; nothing to do for it in a walk.
- Frames: `ppp walk` scrolls the app's containers to show a marked control and measures the frame inside every clipping parent, because a frame around the whole box landed on other content [B] (PAPPS-20261103-WIN-06).
- After a marked picture it scrolls the containers back: after a marked picture a preview stood outside the window and the next click had no effect, while the same steps unmarked worked [B]; scrolling back is the suspected cure [O] (GEN-20261105-WIN-04).
- A frame's number sits at its top left, moved inside the picture when the control touches the app's edge, where it was cut off [B] (GEN-20261105-WIN-03).
- Before each picture text selections are cleared, and the pointer leaves the app unless the step before is a `hover`: a classic button under the pointer showed its selected fill without readable text [B] (PAPPS-20261104-WIN-01).

## State of the evidence
| Statement | Status |
|---|---|
| Edge through Playwright without a browser download, single sign-on in the own profile, conditional access does not block | [B] |
| 80 controls of an app found through `data-control-name`; console and HTTP errors recorded | [B] |
| Clicks and masks at the measured position of a control | [O] tested only on a stand-in with frames |
| Typing into the control's input, frames on its visible part, no selection, the app's frame only: the technique in a project camera (PAPPS-20261103-WIN-05, PAPPS-20261103-WIN-06) is [B] | [O] in `ppp walk`, tested on a stand-in |
| `expect` on real canvas markup: text and field values as the runtime renders them | [O] tested only on a stand-in |
| `--diagnose`: which errors of connectors the runtime shows as failed requests, and the headers `x-ms-request-url` and `x-ms-request-method` | [O] |
| `--video` on the company computer: ffmpeg download, quality on real apps | [O] |
| A second account in its own profile despite single sign-on on the company computer; how the canvas runtime marks disabled controls | [O] |
| Findings L1–L5 and A1–A3 on real canvas markup, especially L3, L4, the roles behind A1 and the wait for a gallery | [O] tune with `ignore` or a lesson |
| L3 on text rectangles and L8 as measured by `ppp walk`; the cause, a clipping box inside dropdowns and combo boxes, is [B] (PAPPS-20261103-WIN-02, PAPPS-20261103-WIN-03) | [O] |
| L6 and L7 as measured by `ppp walk`; the cause, the border layer `appmagic-borderfill-container` with `margin: -0.5px`, is [B] (PAPPS-20261103-WIN-01) | [O] |
