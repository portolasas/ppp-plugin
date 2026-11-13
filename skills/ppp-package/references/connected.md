# Connected project: ppp exports and imports

A project is **connected** when `project.json` names an `environment`: `ppp` then exports, imports and reads the result via pac. Status per statement: [solutions.md](solutions.md). Drift, a failed import, pac failing, a restore: [connected-trouble.md](connected-trouble.md). Creating a solution and the members of the transfer solution: [connected-create.md](connected-create.md). The move into a test environment: [connected-move.md](connected-move.md).

## What changes in the package cycle
`ppp export` replaces the user's export at the start of every package, after the scaffold of step 2 and after step 6 (the tenant's state becomes the next base). `ppp import` replaces the import of step 6; a card if it asks.

## Export
`ppp export` fetches the package solution, unpacks and commits it as "Export <name> <version>". Only the portal's dialog raises the online version [B].
- Lines with `M`, `D` or `??` are manual tenant changes (the diff shows them), now in the working copy: compare with the notes in `STATE.md`, remove those settled.
- Mode large: the transfer solution, as `ppp pack`. The main solution comes with `ppp export --solution <Name>`: at intake, after a scaffold created in it, and when the user asks.
- Refusals: see "Refusals" in [connected-trouble.md](connected-trouble.md).

Done when it reports a commit or "Same content as the last commit."

## Import
`ppp import` takes the newest `ppp pack` package. A call that reaches the drift check exports anew (`CONFIRM FIRST` too). Refusals: see "Refusals" in [connected-trouble.md](connected-trouble.md). Act on the first word of the answer:

| Answer | What happened | You |
|---|---|---|
| `IMPORTED:` | Package online, job ended; below record, switches, bindings. Failures in the record are a `WARNING` line. The record's "The original workflow definition has been deactivated and replaced." is the usual message per replaced flow: no card, no `WARNING` line. `Import record: not readable yet` is no deviation (`ppp tenant --log` shows it later) | Report these lines; clear each `WARNING` or card it. Then one card for what stays by hand (changed flows saved in the designer, critical scenarios), then `ppp export` |
| `CONFIRM FIRST` | Nothing imported; a card is due | Show its tenant-step card ("Import", "Not now"); then the same command with `--confirmed` |
| `DRIFT:` | Nothing imported; the tenant differs from the base | Show the files and lines; card: take the changes over (recommended) or overwrite them (`--accept-drift`, then `CONFIRM FIRST`); see "Drift" in [connected-trouble.md](connected-trouble.md) |
| `RUNNING:` | The server still imports or does not show it yet (queue, long upload) or the version is online but the job has not ended (then record and switches are not final yet). pac was ended on purpose; the server imports on without it | Wait the "Usual here: about … from the start of an import to IMPORTED" it names, then the same command: it waits, starts no second import |
| `FAILED:` | Rejected (reason from pac or this import's job), or the server showed no job 30 minutes after the start (then no record; `ppp tenant` shows the state) | "Failed import" in [connected-trouble.md](connected-trouble.md) |
| `ERROR:` | A check refused, or pac did not get through | "Refusals" and "When pac does not get through" in [connected-trouble.md](connected-trouble.md) |

- **After `IMPORTED`** `ppp pack` and `ppp import` refuse until `ppp export` ran (a `ppp unpack` of an export of the same version counts; `--compare` and `--no-commit` do not).
- **Waiting**: `--wait <seconds>` (default 100; `--wait 540` where the terminal allows).

Done when `ppp export` after `IMPORTED` reports "Same content as the last commit." or an explicable diff.

## Backup
Before each import the tenant's state is saved as `exchange/tenant/<Name>/before_<version>.zip` until the next import (`imports.jsonl` logs imports). `ppp tidy` leaves `exchange/tenant/` alone. Back: "Restore" in [connected-trouble.md](connected-trouble.md).

## Reading the tenant
`ppp tenant`, `ppp connect` show "Usual here: export about …, import about … (a whole ppp import up to IMPORTED, checks and backup included)"; `ppp tenant` also shows versions against the project, flows that are off, connection references without or with a broken connection. `--log` adds the last import's record, `--values` variable values (on request), `--write` saves bindings and switches in `environments/<alias>.json`. Run history stays a card: ppp does not read flow runs.

## Setting the connection
- `ppp connect "<environment name>" --role <development|test|production> --in-use <yes|no> --confirm-import <yes|no>` finds the environment by its exact display name (similar names are suggested), writes its address into `environments/<alias>.json`; without a name it refreshes. `--off`: offline. It also prints a line on the publisher of the settings (as in the settings, missing, differing): [connected-create.md](connected-create.md), "Create a solution".
- An environment of role `test` is the target of a move: `ppp connect "<name>" --role test --target` connects a second one and leaves `project.json` as it is: [connected-move.md](connected-move.md).
- pac does not name an environment's role: the first `ppp connect` needs `--role`, then the role in `environments/<alias>.json` counts. Without a role `ppp connect` and `ppp import` refuse and explain the roles.
- The default environment is the standard; working in an own development environment is the user's free choice.
- `--confirm-import yes` asks for a card before every import, `no` only on drift and on the first import of ppp from this project into the environment (also if the solution is there already); `--in-use yes` and role `test` keep it before every import.
- Address and IDs of an environment stay in `environments/`, out of lessons, skills, chat.

## What stays with the user
- Scaffolds (an empty first solution excepted: `ppp import --create` builds it after a card), removing members of the transfer solution (ppp adds them: `ppp members`), the cards after an import, switching flows, connections, "paste code", publishing an app, deleting.
- Production: `ppp import` refuses it; governance way (ppp-golive).

The tenant is reached through `ppp connect`, `export`, `import`, `tenant` and `members` only. Where hooks run, a direct call of `pac` is refused, also a command line that only quotes it (a commit message) where `pac` stands in the quoted text after `;`, `|`, `&`, `(` or at the start of a line: write the text with the file tool or rephrase it. What these do not offer goes to the user on a card.
