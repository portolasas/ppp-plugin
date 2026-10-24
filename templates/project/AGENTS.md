# {{name}}

<The project in five lines: purpose, users, solution parts, special features. No current status here; that is in STATE.md.>

**Read [STATE.md](STATE.md) first.** Prefix, solutions, modules and mode are in [project.json](project.json) only.
In VS Code work with the agent "ppp" (agent picker); it carries the rules of ppp.

## Folders
- `specs/`: living specification, one file per capability
- `changes/`: development packages `NNN-name/`; finished ones in `changes/archive/`
- `decisions/`: one file per decision, `NNN-name.md`
- `components/`: what ppp builds and maintains, one folder per active module with an inventory README
- `solution/`: tenant state, unpacked from the last export with `ppp unpack`
- `exchange/`: ZIPs from and to the tenant, not in git; `exchange/archive/` keeps the imported package of each finished package
- only when present: `inputs/` source material unchanged · `environments/` IDs per environment · `tests/` local tests · `prototype/` click mock-up · `lessons/` lesson proposals · `docs/` handbook, training, six-sigma, project material · `legacy/` old files of an adopted project, unchanged; read there only when a question about the history cannot be answered from `specs/`, `decisions/` and `components/`

## Project rules
- none yet
