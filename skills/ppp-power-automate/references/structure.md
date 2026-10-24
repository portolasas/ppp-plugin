# Structure of a flow

## Scopes, runAfter, references
- `runAfter` may only name **sibling** actions on the same level; otherwise the import is rejected. Action names are unique per flow. [B] (`ppp verify` C7)
- Every action referenced in an expression (`outputs`, `body`, `actions`, `result`) must be a transitive `runAfter` predecessor in the reachable scope path, or an enclosing scope; otherwise the designer rejects the save with `InvalidTemplate`. A checker that only tests whether the action exists misses this [B, live confirmation of the fix open] (PA-20261012-MAC-01). `ppp verify` C13 checks the paths; `wdl_sim` fails on a reference to an action that has not run.
- Reordering can change stored status or result values when a commit action runs parallel to the result building: after such a fix compare stored fields, response and write order for every test case (PA-20261012-MAC-01).
- Pattern: `Try` / `Catch` (runs after Try failed or timed out) / `Finally`, status and error message written to the record. [B]

## Nesting
- At most level 8, top level = 0; every Scope, If, Foreach, Until and Switch raises the level of its content by 1. Deeper actions are rejected on save and import ("nested at level 9 which exceeds the maximum nesting limit of 8") [B] (PA-20261008-MAC-01). `ppp verify` C12.
- Keep generated flows flat: conditions as siblings instead of nested (a `Compose` "route" plus one If per case); in loops guard expressions instead of If (empty arrays when a case does not apply; append messages always and filter empty ones after the loop).

## Loops and Terminate
- An `Until` loop counts as succeeded when its last iteration succeeded; failures in earlier iterations and a reached count or timeout limit do not fail it [D]. `"operationOptions": "FailWhenLimitsReached"` makes a reached limit fail the loop [D, not tried in Power Automate yet]. Record a failure in a variable before the next iteration, stop on malformed data, and report counts as complete only when the whole loop succeeded (PA-20261023-WIN-01).
- `Terminate` inside a `foreach` is rejected on save (`InvalidWorkflowRunAction`) [B] (PA-20260929-MAC-02). Collect or mark errors in the loop, terminate after it; with invalid data block the write path explicitly so the error handling cannot end as apparent success. `ppp verify` C10.

## Child flows
- A child flow ends on **every** path (success and catch) with `Respond to a PowerApp or flow` or `Response`. [B]
- In chains the innermost child is built first. [B]
- A failing child flow was started again at least seven times while the parent waited; switching the parent off did not stop it, only cancelling the concrete run did. Cause (action retry policy or platform) [O] (PA-20260925-MAC-02). Before tests check the retry setting of `Run a Child Flow`; on failure cancel the concrete parent run and set the record visibly to error.

## Retry
- Connector actions without an explicit retry policy repeat on 408, 429 and 5xx [D]. For hard call limits (e.g. at most two prompt calls) set `retryPolicy.type = none` and check after the import that the designer shows "Retry policy: None". [B] (`ppp verify --retry-none`)
- Own retry logic only **before** the first write, never after partial writes. [B]
- A catch path must not overwrite a success: guard the error write with a status check. [B]

## Idempotency and test data
- Every write has a stable key from the source (e.g. `Upload|<File.UniqueId>`), checked before creating. [B]
- Tests with fresh data: new file, new record, new run ID; failed runs stay as evidence. [B]
- A test that needs a pre-registered record creates it first; a missing row shows as HTTP 400 on `…/items()`. [B]
- Acceptance tests with many manual steps (creating list entries, changing group members, starting flows several times, reading logs, cleaning up) become a **test helper flow** [B] (PA-20261008-MAC-02): manual trigger with input "Phase", prepares its test data from existing data and remembers the initial state, calls the flow under test per step with "Run a Child Flow", checks each expectation, always cleans up (also after abort, plus a phase for cleanup only). Required: stop without writing when test data exists already; restore the initial state; test entries to the recycle bin (`…/items(<id>)/recycle()`), not deleted; result rows without personal data. The card for the user stays short: import, start, read the result.
