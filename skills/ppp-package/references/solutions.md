# Solutions: export, package, import

Status per statement: **[B]** observed in the tenant, **[D]** documentation, **[O]** open.

## Package by hand or as package
- Up to about five field or expression changes on existing actions: by hand in the designer, noted in `STATE.md` (ANFORDERUNGEN W12); new scopes or loops, many similar actions, long JSON bodies, new flows after a scaffold: a package. Prompt texts always directly in Prompt Builder. When unsure, ask. [B]
- A package is the **main solution without apps**: all flows, prompts, environment variables and connection references (UEBERGANG Ü-10). This replaces the earlier rule "never import the main solution as transfer package": the risk is accepted on purpose — a manual change in any flow of the solution that is not rebuilt exactly from its note is overwritten by the next package (Ü-11, ARBEITSWEISE A-6).
- **In a project of mode large the package is the transfer solution `<prefix>Transfer`** (role `transfer` in `project.json`; user, 2026-10-24) [B]: an unmanaged solution with only the components the current package changes, plus their connection references and environment variables. The main solution stays complete and is not packed during development; `ppp inventory`, `verify`, `pack` and `setupflow` take the transfer solution unless `--solution` names another. Components enter with *Add existing* (same identity, never a copy) and leave with *Remove from this solution* once no planned package changes them, never deleted from the environment. New components are created in the main solution, then added.

## Package facts [B]
- Workflow JSON in an export is indented by two spaces, with CRLF and UTF-8 **without** BOM; `pac solution unpack` keeps the workflow files byte-identical, and `pac solution pack` takes them over unchanged (`ppp pack` checks this).
- Change only the intended workflow files and the version; every other file stays byte-identical, line endings unchanged (`ppp verify` C4, C6).
- Edit the workflow JSON as a file with small targeted edits; never re-serialize a whole definition through objects of a script language (failed repeatedly for nested definitions). Generators replace only the value of `definition.actions` in the original text (`setupflow.replace_value`).
- For SharePoint `executeFlow` use the complete value from "Export › Get flow identifier".

## Export
- The export dialog proposes the next version after an import (1.0.0.10 imported → 1.0.0.11 proposed; the content equals the package). Cards say "version as proposed" instead of a fixed file name; the base is always the export with the highest version [B] (SOL-20261008-MAC-02).
- After every scaffold card check that each flow name occurs once in the export (`ppp unpack` lists the flows and warns on duplicates). With duplicates build the flow the app or the parent flows use (workflow ID in the `.msapp`, `Properties.json` or `References/DataSources.json`, or `workflowReferenceName` of the parent flows), leave the other one unchanged and let the user delete it [B] (SOL-20261009-MAC-01).
- If a build needs another manual flow and the solution holds an unused flow with fitting connection references, a generator may repurpose it instead of asking for a new scaffold: change only title and description of existing trigger inputs (internal keys stay), copy environment-variable parameters and templates of other actions from flows of the same export; the display name of the flow stays, so name it in cards [B] (SOL-20261008-MAC-01).

## Import checklist
**Before**: `ppp pack` without errors, SHA-256 in the report; the package rests on the last export plus the rebuilt manual changes; an app changed in Studio was saved and published.

**Import (user)**: make.powerapps.com › Solutions › Import solution › the ZIP from `exchange/`; assign the connection references; note warnings about replaced or deactivated definitions.

**After**: open each changed flow once and **save** (this proves the designer-required fields; the flow checker runs with it); check fields named as critical in the code view (e.g. retry policy, sentinel); then the critical scenarios. Whether flows are on is the user's matter.

**Import failed**: keep the error text word for word, never import the same ZIP again; typical causes in the skill ppp-power-automate (`references/errors.md`); the next package gets a new version.

## Documentation and tests
No personal data and no tokens in documentation, tests or tickets: field names, types and counts only. Raw trigger outputs often hold names and short-lived URLs with tokens. Exports with personal data may be read and evaluated for the work itself.
