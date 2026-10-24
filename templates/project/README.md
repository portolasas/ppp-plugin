# {{name}}

<Purpose in two to five sentences: which process, for whom, what changes for the users.>

## Overview
- Users and owners: <business unit, contact persons>
- Solution parts:
{{module_lines}}
- Current state: [STATE.md](STATE.md) · plan: [ROADMAP.md](ROADMAP.md)

## Where to find what
| Folder | Content |
|---|---|
| [specs/](specs/) | what the solution does |
| [components/](components/) | flows, screens and lists in detail |
| [decisions/](decisions/) | why it is built this way |
| [changes/](changes/) | development packages; finished ones in `archive/` |
| `docs/` | handbook, training, project material (when present) |
| [solution/](solution/) | tenant state from the last export |

## Working on this project
ppp builds and checks the solution offline; tenant steps such as export, import and tests are done by hand, guided by cards. VS Code: agent "ppp"; Claude Code: plugin ppp.
