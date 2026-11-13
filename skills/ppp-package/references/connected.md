# Connected project: ppp exports and imports

A project is **connected** when `project.json` names an `environment`: `ppp` then fetches the export, imports the package and reads the result via pac. Status per statement as in [solutions.md](solutions.md).

## What changes in the package cycle
`ppp export` replaces the user's export: at the start of every package (the diff shows manual tenant changes), after the scaffold of step 2 (the card ends with it) and after step 6 (the tenant's state becomes the next base). `ppp import` replaces the import of step 6; a card if it asks.

## Export
`ppp export` fetches the package solution, unpacks and commits it as "Export <name> <version>". pac keeps the version online; only the portal's dialog raises it [B].
- Lines with `M`, `D` or `??` are manual tenant changes, now in the working copy: compare with the notes in `STATE.md`, remove those they settle.
- It refuses uncommitted changes in `solution/<Name>/`, `--force` too: commit them (the version `ppp pack` raised is one); it refuses committed work the tenant lacks: commits since the last export (after an import too), a packed, unimported version. `ppp export --compare` lists the differing files, changes nothing. `--force` replaces that committed work (it stays in git) only after a decision card.
- Mode large: the transfer solution, as `ppp pack`; the main solution with `ppp export --solution <Name>` (at intake, after a scaffold created in it).

Done when it reports a commit or "Same content as the last commit."

## Import
`ppp import` takes the newest `ppp pack` package. It refuses: uncommitted changes in `solution/<Name>/` (commit first); a package packed before the last export (`ppp pack --version <next>`); a version whose import failed, repacked too. A call that reaches the drift check exports the backup anew (`CONFIRM FIRST` too), taking as long as an export. Act on the first word of the answer:

| Answer | What happened | You |
|---|---|---|
| `IMPORTED:` | Package online, job ended. Below: import record, flow switches, bindings. Failures in the record are a `WARNING` line; show warnings to the user. `Import record: not readable yet` is no deviation (`ppp tenant --log` shows it later) | Report these lines; clear each `WARNING` or card it. Then one card for what stays by hand (changed flows opened and saved in the designer, critical scenarios the walk misses), then `ppp export` |
| `CONFIRM FIRST` | Nothing imported; a card is asked for | Show the tenant-step card it describes, answers "Import", "Not now"; then the same command with `--confirmed` |
| `DRIFT:` | Nothing imported; the tenant differs from the package's base | Show the files (`ppp export --compare`); card: take the changes over (recommended) or overwrite them (`--accept-drift`, then `CONFIRM FIRST`) |
| `RUNNING:` | The server still imports or does not show it yet (queue, long upload), or the version is online but the job has not ended (record and switches not final); pac was ended on purpose | Say so in one line, wait the "Usual here: import about …" it names, then the same command: it waits, starts no second import |
| `FAILED:` | Rejected (the reason is the one pac names or from this import's job), or the server showed no job 30 minutes after the start (then no record; `ppp tenant` shows the state) | See "Failed import" |
| `ERROR:` | A check refused, or pac did not get through | See "When pac does not get through" |

- **Take drift over**, in this order: commit the work, `ppp export --force`, rebuild the work on the tenant's state (`git cherry-pick` its build commits or run its generators again), `ppp verify`, `ppp pack --version <next>` (the old package is refused), `ppp import`.
- **Waiting**: `--wait <seconds>`: how long one call waits (default 100; `--wait 540` where the terminal allows).

Done when `ppp export` after `IMPORTED` reports "Same content as the last commit." or an explicable diff.

## Failed import
`FAILED:` uses the ZIP and its version up. The work stays; `ppp export` will not replace it. `ppp tenant --log` gives the record's error texts (none after the 30 minutes). Find the cause (skills ppp-diagnose, ppp-power-automate `references/errors.md`), fix it, `ppp verify`, `ppp pack --version <next>`, `ppp import`.

Done when the next import answers `IMPORTED:`.

## When pac does not get through
`ERROR: <KIND>:` below; a refused check is `ERROR:` without a kind and names the next step.
| Kind | Meaning | You |
|---|---|---|
| `AUTH` | pac is not signed in here | Card, as offline; the user signs in (`pac auth create`), name it once |
| `DENIED` | The account may not do this in the environment | Card, as offline |
| `SYNTAX` | pac takes the call differently than ppp expects | Card, as offline; lesson proposal |
| `TIMEOUT` | No answer in time | Once more; then a card, as offline |
| `BUSY` | Another import of this solution runs | Wait; `ppp tenant` shows the state |

`AUTH`, `SYNTAX` and `BUSY` at the start of an import leave the ZIP unused: the same command can run again. So does `ERROR:` without a kind when pac skips the import because the version online is not lower: pack the version the message names (after a restore, `ppp import --restore` again). "As offline" means the card of SKILL.md step 2 or 6; the user's export goes in with `ppp unpack`. The project stays connected.

## Backup and restore
Before each import the tenant's state is saved as `exchange/tenant/<Name>/before_<version>.zip` until the next import; `imports.jsonl` beside it logs imports.

`ppp import --restore` brings the newest backup back, only on the user's decision: `CONFIRM FIRST`, then "Restore" and `--confirmed`. The backup's components get their old content under a higher version; what an import added since stays, a new flow for example [B]. Apps need `--with-apps`. `ppp export` then shows later packages' changes as reverted (they stay in git). `ppp tidy` spares `exchange/tenant/`.

## Reading the tenant
`ppp tenant` shows "Usual here: export about …, import about …", versions against the project, flows that are off, connection references without or with a broken connection. `--log` adds the last import's record, `--values` environment variable values (on request), `--write` saves bindings and switches into `environments/<alias>.json`.

## Setting the connection
- `ppp connect "<environment name>" --role <development|test|production> --in-use <yes|no> --confirm-import <yes|no>` finds the environment by its exact display name, writes its address into `environments/<alias>.json` (similar names are suggested); without a name it refreshes. `--off` makes the project offline.
- pac does not name an environment's role: the first `ppp connect` needs `--role`, then the role in `environments/<alias>.json` counts. Without a role `ppp connect` and `ppp import` refuse and explain the three roles.
- The output has "Usual here: …" and, for the default environment, a `RECOMMENDED` line: an own development environment, if the user has one, because export and import run faster there; the default environment works as well. Tell the user once, with the times, not again at each connect.
- `--confirm-import yes` asks for a card before every import, `no` only on drift and a first import; `--in-use yes` (productive use) keeps it.
- Address and IDs of an environment stay in `environments/`, out of lesson proposals, skills, chat.

## What stays with the user
- Scaffolds, transfer solution members, the cards after an import, switching flows, creating or repairing a connection, "paste code", publishing an app, deleting.
- Production: `ppp import` refuses role `production`; governance way (ppp-golive).

The tenant is reached through `ppp connect`, `export`, `import` and `tenant` only. Where hooks run, a direct call of `pac` is refused, also a command line that merely quotes `pac` after `;`, `|`, `&`, `(` or at a line start (a commit message): write the text with the file tool. What these do not offer goes to the user on a card.
