# Reviewing a run

## Measured findings
The measured findings are hints:
- Layout: L1 outside the window, L2 outside the parent, L3 text cut off by its control or by a clipping box inside it, L4 overlap, L5 image not loading, L6 a button label on more than one line, L7 a painted border cut by a parent, L8 a word broken over two lines.
- Usability: A1 clickable without text or `AccessibleLabel`, A2 click area under 24 px, A3 text contrast under 4.5:1.

L3 is measured on the text's own rectangles, so the chevron of a dropdown and the frame of a combo box count and a small overhang is font metrics (PAPPS-20261103-WIN-02, PAPPS-20261103-WIN-03).

The result lines name each finding once, at its first picture, with the number of further pictures; `report.json` keeps the findings of every picture. A finding that is intended goes into `ignore` of the walk.

## Comparison with the last run
From the second complete run on, every picture is compared with the last one; the result lines name each changed picture with its area and a diff in `exchange/walks/<name>/diff/` (changed pixels red). Pictures that differ in size by up to 2 px, as the app frame did by one pixel between runs [B], are compared on their common area, and the line names the size change. Look at each diff: a change outside the package's scope is a finding. Moving data such as dates also shows up there; cover it with `mask` if it gets in the way.

## Load times
The run also measures time and requests: from the action to the last visible change, for the start and each `click`, `type`, `key` and `wait`, all in `report.json`, those from one second on in the result lines. A step clearly slower than in the last complete run is a warning; go through ppp-power-apps (performance) for it. Compare like with like: the first start of a fresh profile is slower, and a second viewport runs in a warm browser.
