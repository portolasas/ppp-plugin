---
name: ppp-setup
description: Setup of ppp on this computer - checks what ppp needs (Python, git, pac, Playwright with Edge and ffmpeg, python-docx, Word, the packages of bi-design) and installs the missing Python packages. Use when the user asks to check or set up ppp, on a new computer, or when a command reports a missing package or program.
---

# Set up ppp on this computer

`ppp setup --check` lists each part ppp uses with `ok` or `missing` and the command that needs it; it changes nothing. `ppp setup --install` installs the missing Python packages with pip into the Python that runs ppp, then the ffmpeg of Playwright, and checks again. Programs (Python, git, pac, Edge, Word) the user installs; the report names where each comes from. Outside a ppp project, `ppp` is the session's `Tool call`, else the line in `~/.ppp/tool-call.txt`.

1. **Check.** Run `ppp setup --check` as the first call. Show in the chat which parts are missing and which command each one serves, grouped by the last line of the report: `RESULT: complete`, `ppp works; missing for single commands`, or `incomplete, required` (Python or git: ppp cannot work without them).
2. **Install.** When the report ends with `ppp setup --install installs: …`, ask on one decision card: install these now (recommended; pip downloads them from the internet into the Python that runs ppp) or not now. On yes run `ppp setup --install`. When pip fails, show its message; behind a proxy the user sets it once with `pip config set global.proxy http://<proxy>:<port>`, then run `ppp setup --install` again.
3. **Programs.** For each missing program, name where it comes from as the report says and which command lacks it until then. Python and git are required; Edge, Word and pac serve single commands (`ppp walk`, `ppp guide --word`, `ppp unpack` and `ppp pack`). When the user reports a program installed, run `ppp setup --check` again.
4. **Hooks in VS Code.** When the report shows `missing` for `Python of the VS Code hooks` (Python from a conda or mamba environment, off `PATH`), run `ppp setup` once without an option: it records this Python for the hooks in `~/.ppp/python.txt`. Then the user runs "Developer: Reload Window".

Done when the last `ppp setup --check` of this turn ended with `RESULT: complete`, or the user read each part still missing with the command it serves and where it comes from.
