# Change path and notation

## Change path
| Situation | Path |
|---|---|
| up to about 5 properties or formulas on existing controls | in Studio, formula in Studio notation (card); with a generator, take the change into it in the next package |
| new screen or section, repetitions, many controls restyled | YAML → "paste code" |
| theme, labels, lookup tables, user-defined functions | the whole App.Formulas block, replaced completely |
| a canvas app inside a solution ZIP | never edited in the package |

Replacing a pasted screen: delete the old screen first, or paste under a new name and delete the old one after the check; with the same name Studio silently appends a suffix [O].

## Notation, the most frequent error source
- **YAML ("paste code", `*.pa.yaml`) always in en-US, comma format**, also in a German Studio [B] (PAPPS-20260926-MAC-01).
- **Formula bar, property fields and App.Formulas in the Studio notation** [B]:

  | Notation | arguments and records | chaining, end of formula | decimal |
  |---|---|---|---|
  | de-DE | `;` | `;;` | `,` |
  | en-US | `,` | `;` | `.` |
- Converting en-US to de-DE, outside strings, 'identifiers' and comments, in this order: `;` to `;;`, `,` to `;`, `.` to `,` only between digits. Keep one en-US source and produce de-DE with `ppp formulas` (or `pfx.nach_de` in a generator). [B]
- Every instruction names the notation: "formula (de-DE, into the formula bar of <control>.<property>)".
