# Connected project: ppp exports and imports

A project is **connected** when `project.json` names an `environment`: `ppp` then fetches the export, imports the package and reads the result through pac. Status per statement as in [solutions.md](solutions.md).

## What changes in the package cycle
| Step | Offline | Connected |
|---|---|---|
| Start of a package | the last export is the base | `ppp export` first; its diff is what was changed by hand in the tenant |
| 2 Scaffold | the card ends with the export | the card ends with the scaffold; then `ppp export` |
| 6 Import | card: the user imports and reports | `ppp import`; a card only when it asks |
| After 6 | `ppp unpack` of the next export | `ppp export` commits the tenant's state as the next base |

## Export
`ppp export` fetches the package solution, unpacks it and commits "Export <name> <version>". pac keeps the version online; only the portal's dialog raises it [B].
- Lines with `M`, `D` or `??` are manual tenant changes, now in the working copy: compare them with the notes in `STATE.md`, remove the notes they settle.
- It always refuses uncommitted changes in `solution/<Name>/`, `--force` too: commit them (the version `ppp pack` raised is one). It refuses committed work the tenant does not have: commits since the last export (after an import too), a packed, unimported version. `ppp export --compare` lists the differing files and changes nothing. `--force` replaces that committed work (it stays in git): only after a decision card.
- Mode large: it takes the transfer solution, as `ppp pack` does; the main solution with `ppp export --solution <Name>` (at intake, after a scaffold created in it, on request).

Done when it reports a commit or "Same content as the last commit."

## Import
`ppp import` takes the newest package of `ppp pack`. It refuses: uncommitted changes in `solution/<Name>/` (commit first, the version `ppp pack` raised included); a package packed before the last export (`ppp pack --version <next>`, as the message names); a version whose import failed, repacked too. A call that reaches the drift check exports the backup anew (`CONFIRM FIRST` too): it lasts as long as an export. Act on the first word of the answer:

| Answer | What happened | You |
|---|---|---|
| `IMPORTED:` | The package is online. Below it: import record, flow switches, bindings. Failures in the record are a `WARNING` line; with warnings a line follows to show them to the user. `Import record: not readable yet` is no deviation (`ppp tenant --log` shows it later) | Report these lines; clear each `WARNING` or put it on a card. Then one card for what stays by hand only (each changed flow opened and saved in the designer, the critical scenarios the walk does not cover), then `ppp export` |
| `CONFIRM FIRST` | Nothing was imported; a card is asked for | Show the tenant-step card it describes, answers "Import" and "Not now"; after "Import" the same command with `--confirmed` |
| `DRIFT:` | Nothing was imported; the tenant differs from the package's base | Show the files (`ppp export --compare`); decision card: take the changes over (recommended) or overwrite them |
| `RUNNING:` | The server still imports or does not show the import yet (queue, long upload); pac was ended on purpose | Say so in one line, then the same command: it waits, starts no second import |
| `FAILED:` | The import was rejected (the reason is from this import's job), or the server showed no job 30 minutes after the start (then no record; `ppp tenant` shows the state) | See "Failed import" |
| `ERROR:` | A check refused, or pac did not get through | See "When pac does not get through" |

- **Take drift over**, in this order: commit the work, `ppp export --force`, rebuild the work on the tenant's state (it stays in git: `git cherry-pick` its build commits, or run its generators again), `ppp verify`, `ppp pack --version <next>` (the old package is refused), `ppp import`.
- **Overwrite drift**: `ppp import --accept-drift` (then `CONFIRM FIRST`).
- **Waiting**: `--wait <seconds>` sets how long one call waits (default 100; `--wait 540` where the terminal tool allows). `RUNNING` names how long the last import there took: wait that long before the next call.

Done when `ppp export` after `IMPORTED` reports "Same content as the last commit." or a diff you can explain.

## Failed import
`FAILED:` uses the ZIP and its version up. The work stays; `ppp export` refuses to replace it.
`ppp tenant --log` gives the record's error texts (none after the 30 minutes). Find the cause (skills ppp-diagnose, ppp-power-automate `references/errors.md`), fix it, `ppp verify`, `ppp pack --version <next>` as the message names, `ppp import`.

Done when the next import answers `IMPORTED:`.

## When pac does not get through
`ERROR: <KIND>:` below; a refusal of the checks is `ERROR:` without a kind and names the next step.
| Kind | Meaning | You |
|---|---|---|
| `AUTH` | pac is not signed in on this computer | Card, as offline. Signing in (`pac auth create`) is the user's; name it once |
| `DENIED` | The account may not do this in the environment | Card, as offline |
| `SYNTAX` | pac takes the call differently than ppp expects | Card, as offline; lesson proposal |
| `TIMEOUT` | No answer in time | Once more; then a card, as offline |
| `BUSY` | Another import of this solution is running | Wait; `ppp tenant` shows where it stands |

`AUTH`, `SYNTAX` and `BUSY` at the start of an import leave the ZIP unused: the same command can run again later. "As offline" means the card of SKILL.md step 2 or 6; the user's export enters with `ppp unpack`. The project stays connected.

## Backup and restore
Before each import the tenant's state is saved as `exchange/tenant/<Name>/before_<version>.zip` until the next import; `imports.jsonl` beside it records every import.

`ppp import --restore` brings the newest backup back, only on the user's decision: `CONFIRM FIRST`, after "Restore" with `--confirmed`. The backup's components get their old content under a higher version; what an import added since stays, a new flow for example [B]. Apps need `--with-apps`. Then `ppp export` shows the later packages' changes as reverted (they stay in git). `ppp tidy` leaves `exchange/tenant/`.

## Reading the tenant
`ppp tenant` shows versions against the project, flows that are off, connection references without or with a broken connection. `--log` adds the last import's record, `--values` environment variable values (on request), `--write` saves bindings and switches into `environments/<alias>.json`.

## Setting the connection
- `ppp connect "<environment name>" --role <development|test|production> --in-use <yes|no> --confirm-import <yes|no>` finds the environment only by its exact display name (similar ones are suggested), writes its address into `environments/<alias>.json`; without a name it refreshes. `--off` makes the project offline.
- Without `--role`, an environment of type Production gets the role production; another explicit role prints a `WARNING` line.
- `--confirm-import yes` asks for a card before every import, `no` only on drift and a first import; `--in-use yes` (productive use) keeps it every time.
- Address and IDs of an environment stay in `environments/`, out of lesson proposals, skills and chat.

## What stays with the user
- Scaffolds, members of the transfer solution, the cards after an import.
- Switching flows, creating or repairing a connection, "paste code", publishing an app, deleting anything.
- Production: `ppp import` refuses role `production`; that goes the governance way (skill ppp-golive).

The tenant is reached through `ppp connect`, `ppp export`, `ppp import` and `ppp tenant` only. Where hooks run, a direct call of `pac` is refused, also a command line that merely quotes `pac` in a text after `;`, `|`, `&`, `(` or at a line start (a commit message): write the text with the file tool or reword it. What these commands do not offer goes to the user on a card.
