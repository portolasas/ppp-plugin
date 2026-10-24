# Third-party templates

ppp adopts single skills of other packages as templates and adapts them (PLUGIN PL-10). No package is included as a whole, and nothing updates automatically. Checked on 2026-10-14, adopted on 2026-10-20.

| Source | Path at the commit | Used in | Changes |
|---|---|---|---|
| [mattpocock/skills](https://github.com/mattpocock/skills) @ `49dd158d1076134a641b33efb035946536778336` | `skills/productivity/grilling/SKILL.md` | `skills/ppp-clarify` | rounds over the frontier of a design tree, recommended answer first, facts found by the agent; questions as cards instead of numbered text, no subagents, depth by mode, results in `specs/` |
| same | `skills/productivity/to-questionnaire/SKILL.md` | `skills/ppp-clarify` (questionnaire) | condensed; file in `docs/project/`, answers back into `inputs/` |
| same | `skills/engineering/domain-modeling/SKILL.md`, `ADR-FORMAT.md` | `skills/ppp-clarify` (decisions) | only the three criteria for recording a decision; format is the short MADR of ppp (`templates/files/decision.md`) |
| same | `skills/engineering/diagnosing-bugs/SKILL.md` | `skills/ppp-diagnose` | feedback loop from exports, `wdl_sim` and reference calculations instead of tests against a running system; tenant evidence by cards |
| same | `skills/engineering/prototype/SKILL.md`, `UI.md` | `skills/ppp-prototype` | one HTML file with JSON data for a planned app, structural variants in a bottom bar; no routes, no branches |
| [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) @ `9111a7654d7800391459431fff4eaf66e33a3d2e` | workflow and file format (`openspec/changes/*/proposal.md`, `tasks.md`, `specs/*/spec.md`; `docs/workflows.md`) | `skills/ppp-package`, `templates/files/` (proposal, tasks, design, spec, spec delta) | files instead of the Node CLI; specs as one file per capability; package folders numbered `NNN-name`; critical scenarios added to the proposal |
| [obra/superpowers](https://github.com/obra/superpowers) @ `bb92a77741419a4ab5f06e711a283343f1ada0c3` | `skills/verification-before-completion/SKILL.md` | `core/ppp.agent.md` (rule "evidence before claims") | shortened to one rule |

## Licences
All three sources are under the MIT License with these copyright notices:

- Copyright (c) 2026 Matt Pocock (mattpocock/skills)
- Copyright (c) 2024 OpenSpec Contributors (Fission-AI/OpenSpec)
- Copyright (c) 2025 Jesse Vincent (obra/superpowers)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
