# Connected project: create a solution, transfer solution members

The ordinary cycle: [connected.md](connected.md). Refusals, drift, a failed import, a restore: [connected-trouble.md](connected-trouble.md). The move into a test environment: [connected-move.md](connected-move.md). Status per statement: **[B]** observed in the tenant, **[O]** open, as in [solutions.md](solutions.md). Every "Next:" line a command prints is the next step; it is not repeated here.

## Create a solution
`ppp import --create [--solution <UniqueName> [--transfer]]` builds an empty first solution (version 1.0.0.1, unmanaged) with the publisher of `ppp settings` and imports it into the project's environment. Without `--solution` it is the main solution, with it the transfer solution `<prefix>Transfer`. It is the only way ppp creates a solution or a publisher; ppp never changes an existing publisher.

1. `ppp connect` printed the publisher line. `Publisher <name>: as in the settings.`, `MISSING Publisher …: ppp import --create builds the first solution with it.` and `WARNING prefix … belongs to …` are the cases; read them to the user before the card.
2. The solution is listed in `project.json › solutions` with role `main` or `transfer`; `--create` refuses any other. A new project names its main solution at `ppp init --solution <UniqueName>`. The transfer solution is not entered by hand: `ppp import --create --solution <prefix>Transfer --transfer` (mode large only, only while the project has no transfer solution) writes it into `project.json` itself on the call with `--confirmed` and prints `project.json: <Name> added as the transfer solution; commit it with the export.`; the call that answers `CONFIRM FIRST` changes nothing in the project, and its card says that `project.json` gets the entry.
3. `ppp import --create [--solution <Name>]` answers `CONFIRM FIRST (a new solution with its publisher)`, always, whatever `confirmImport` says.
4. Card with the answers "Create" and "Not now": environment and role, solution and version, empty, the publisher with its four values and whether it is new or in the environment already, and that solution and a new publisher stay in the tenant until the user deletes them by hand (first the solution, then the publisher). After "Create": the command the line ends with, `--confirmed <code>` included.
5. `ppp export --solution <Name>` commits the first base (with the transfer solution, the `project.json` entry too).

| Answer | You |
|---|---|
| `CONFIRM FIRST` | Step 4; `WARNING` lines under it (an option value prefix another publisher uses) go on the card |
| `IMPORTED:`, `CREATED solution …` | Report the lines; a `WARNING` (the solution belongs to another publisher, a value of the publisher differs from the settings) goes to the user before step 5 |
| `RUNNING:` | Run the command its next line names, without `--confirmed`; it starts no second import |
| `FAILED:` | Nothing is online and no version is used up: find the cause (skill ppp-diagnose), then `ppp import --create` again |

Refusals that need you:
- `The publisher … is missing in …, the default environment`: ppp creates no publisher there. Card for the user: the portal dialog it names, with the four values of `ppp settings`; then `--create` again. With the publisher in place `--create` works there too [O: parts observed, the whole not].
- `The publisher … differs from the settings` or `The prefix … belongs to the publisher …`: card with the choice between aligning the settings (`ppp settings --publisher-from <unpacked solution of that publisher>`) and another publisher or prefix (`ppp settings --publisher-prefix …`).
- `project.json names the publisher …, the settings …`: `ppp check` names what to align.
- `--transfer needs mode large`, `project.json names <Name> as the transfer solution already`, `<Name> is the main solution`, `<Name> has the role …`: no second transfer solution and none in another mode; `--transfer` is left out where the project has the entry already.
- `… is in … already` or `solution/<Name>/ exists already`: nothing to create; `ppp export --solution <Name>` takes it into the project.
- `ppp import --create` with a package, `--restore`, `--environment`, `--accept-drift`, `--with-apps` or `--raise-version` is refused: leave them out. `--transfer` without `--solution` or without `--create` is refused.

Offline, without a sign-in or when a card above says so, the card of SKILL.md step 2 stays (the portal creates solution and publisher).

Done when `ppp export --solution <Name>` reports a commit. A creation brought no content: the first package import still counts as the first import of ppp into the environment and asks for its card ([connected.md](connected.md), `--confirm-import`).

Status: the empty package comes from the plugin's template, not from the head of an export of the same environment; an empty solution with a new publisher is observed in a test environment [B], the template itself is [O] until the first `--create` runs there. A new publisher in the default environment is [O] and stays a card. Whether the server refuses a second publisher with the same option value prefix is [O]; ppp only warns.

## Members of the transfer solution
Mode large, role `transfer` in `project.json`, the transfer solution online and unmanaged. `ppp members` lists the members; `ppp members <Name> …` adds flows, environment variables and connection references of the main solution, each at its ID, without a card: only membership changes, no content. Components sit in two solutions at once [B].

1. The names come from the committed `solution/<Main>/`: a flow by its name, a variable by its schema name, a reference by its logical name, regardless of case. If the main solution is not exported yet or has uncommitted changes, `ppp export --solution <Main>` first.
2. A flow brings the connection references and environment variables it uses; the line names them `(with <Flow>)`. Name the other components of the package too.
3. `ppp members <Name> …`, then `ppp members` once to read what the solution holds.
4. `ppp export` takes the transfer solution with its members as the base.
5. Removing goes on a card: Solutions › transfer solution › Remove from this solution, for members no planned package changes. Members the user keeps go into the package unchanged.

| Answer | You |
|---|---|
| `ADDED:` | Report; the members are in the tenant |
| `ALREADY:` | Nothing to do; if only this line came, nothing was called |
| `FAILED: <kind> <name>: <reason>` | Exit code 1; give the reason to the user, one component per line, then card the step by hand (Add existing) for it |
| `MEMBERS:` | `other (<kind>) <objectid>` (`other <objectid>` without a kind): a member the main solution does not name, such as a variable's value (it travels with the export): tell the user |

Refusals that need you:
- `needs mode large and a solution of role transfer`, `<Transfer> is not in <alias>`: create it first (section above, with `--transfer`).
- `No component named …`: the line lists candidates; pick from them. `names <n> components`: give the full name.
- `<Name> is a <kind>` (an app, a table, a role): ppp adds flows, variables and references only; the rest goes on a card.
- `The flow … is not in …`, a flow that uses a reference or variable the main solution lacks, a component with other than one row in the environment: nothing is added; report it to the user.
- `<Transfer> is managed`, `role production: ppp reads there only`: ppp does not add; card.

Done when `ppp members` lists every component of the package and `ppp export` reported a commit or "Same content as the last commit."

Status: adding in the default environment is [O] (observed in a test environment only). That every flow names its variables under `metadata.schemaName` is read from the code, not observed; a variable it does not name is not taken along, so compare the `ADDED:` line with the flow.
