# Solutions: export, package, import

Status per statement: **[B]** observed in the tenant, **[D]** documentation, **[O]** open.

## Package by hand or as package
- Up to about five field or expression changes on existing actions: by hand in the designer, noted in `STATE.md` (ANFORDERUNGEN W12); new scopes or loops, many similar actions, long JSON bodies, new flows after a scaffold: a package. Prompt texts always directly in Prompt Builder. When unsure, ask. [B]
- A package is the **main solution without apps**: all flows, prompts, environment variables and connection references (UEBERGANG Ü-10). This replaces the earlier rule "never import the main solution as transfer package": the risk is accepted on purpose — a manual change in any flow of the solution that is not rebuilt exactly from its note is overwritten by the next package (Ü-11, ARBEITSWEISE A-6).
- **In a project of mode large the package is the transfer solution `<prefix>Transfer`** (role `transfer` in `project.json`; user, 2026-10-24) [B]: an unmanaged solution with the components the current package changes, plus their connection references and environment variables. The main solution stays complete and is not packed during development; `ppp inventory`, `verify`, `pack` and `setupflow` take the transfer solution unless `--solution` names another. Components enter with `ppp members` in a connected project, offline with *Add existing* (same identity, never a copy), and leave with *Remove from this solution* once no planned package changes them, never deleted from the environment; removing stays with the user.
- Removing is recommended, not required: members the user keeps go into the package unchanged from the latest export of the transfer solution (user, 2026-11-03). New components are created in the main solution, then added ([connected-create.md](connected-create.md), "Members of the transfer solution").
- In a connected project `ppp export` and the drift check before an import take the solution that is packed, in mode large the transfer solution ([connected.md](connected.md)).

## Package facts [B]
- Workflow JSON in an export is indented by two spaces, with CRLF and UTF-8 **without** BOM; `pac solution unpack` keeps the workflow files byte-identical, and `pac solution pack` takes them over unchanged (`ppp pack` checks this).
- Change only the intended workflow files and the version; every other file stays byte-identical, line endings unchanged (`ppp verify` C4, C6).
- Edit the workflow JSON as a file with small targeted edits; never re-serialize a whole definition through objects of a script language (failed repeatedly for nested definitions). Generators replace only the value of `definition.actions` in the original text (`setupflow.replace_value`).
- For SharePoint `executeFlow` use the complete value from "Export › Get flow identifier".

## Export
- The export dialog proposes the next version after an import (1.0.0.10 imported → 1.0.0.11 proposed; the content equals the package). Cards say "version as proposed" instead of a fixed file name; the base is always the export with the highest version [B] (SOL-20261008-MAC-02). An export through pac (`ppp export`) keeps the version online and is byte-identical to the portal's export of the same state; `ppp` then takes the commit "Export <name> <version>" as the base [B] (pac test, 2026-11-12).
- After every scaffold card check that each flow name occurs once in the export (`ppp unpack` lists the flows and warns on duplicates). With duplicates build the flow the app or the parent flows use (workflow ID in the `.msapp`, `Properties.json` or `References/DataSources.json`, or `workflowReferenceName` of the parent flows), leave the other one unchanged and let the user delete it [B] (SOL-20261009-MAC-01).
- If a build needs another manual flow and the solution holds an unused flow with fitting connection references, a generator may repurpose it instead of asking for a new scaffold: change only title and description of existing trigger inputs (internal keys stay), copy environment-variable parameters and templates of other actions from flows of the same export; the display name of the flow stays, so name it in cards [B] (SOL-20261008-MAC-01).

## Publisher
- The publisher belongs to the developer, not to a project: stored once per computer in `~/.ppp/settings.json` (`ppp settings`); `project.json` names it in `publisher`. The project's `prefix` is another thing. [D]
- Name: letters, digits and `_`, not starting with a digit. Prefix: 2–8 letters or digits, starting with a letter, not `mscrm`. Choice value prefix: 10000–99999. [D]
- The prefix becomes part of the schema names of environment variables, connection references and tables and cannot be changed after the first component; fix it before. Never the environment's default publisher (random prefix). [D]
- No pac command creates a publisher; the import of the first package does, where the publisher is missing: a connected project builds that package with `ppp import --create` ([connected-create.md](connected-create.md)), offline and in the default environment without the publisher the user creates it in the portal. An empty package created a missing publisher in a test environment [B]; the default environment is [O]. ppp never changes an existing publisher.

## Import checklist
In a connected project `ppp import` runs the checks before the import and reads the result after it ([connected.md](connected.md)); from this list the save in the designer and the critical scenarios stay with the user. An import through pac did not switch a flow: one switched off by hand stayed off, one that was on stayed on [B] (pac test, 2026-11-13); `ppp import` names every switch that changed.

**Before**: `ppp pack` without errors, SHA-256 in the report; the package rests on the last export plus the rebuilt manual changes; an app changed in Studio was saved and published.

**Import (user)**: make.powerapps.com › Solutions › Import solution › the ZIP from `exchange/`; assign the connection references; note warnings about replaced or deactivated definitions.

**After**: open each changed flow once and **save** (this proves the designer-required fields; the flow checker runs with it); check fields named as critical in the code view (e.g. retry policy, sentinel); then the critical scenarios. Whether flows are on is the user's matter.

**Import failed**: keep the error text word for word, never import the same ZIP again; typical causes in the skill ppp-power-automate (`references/errors.md`); the next package gets a new version.

## Documentation and tests
No personal data and no tokens in documentation, tests or tickets: field names, types and counts only. Raw trigger outputs often hold names and short-lived URLs with tokens. Exports with personal data may be read and evaluated for the work itself.
