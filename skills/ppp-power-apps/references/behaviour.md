# Runtime behaviour

## Start and navigation
- `App.OnStart` is not awaited by the first screen [B]. A bootstrap (e.g. a flow that returns the user context) belongs into `OnVisible` of every screen, guarded by `varBootstrapDone`. Constants, theme and labels as named formulas in App.Formulas.
- `Navigate()` in `OnVisible` is rejected by Studio ("navigation away from this screen") [B]. Access locks as an overlay container (`Visible = !varAllowed`).
- Named formulas with records, user-defined functions (`StatusFill(s: Text): Color`) and screen references in named formulas are accepted [B][V].

## Calling flows (Power Apps V2 trigger) [B]
- Required inputs positional, **optional inputs as one record**: `Flow.Run(text; text_1; {text_3: …; text_4: …})` (de-DE).
- Response fields appear exactly in the spelling of the flow's response schema (e.g. `correlationId`).
- Busy state: `Set(varBusy; true);; Set(varResult; Flow.Run(...));; Set(varBusy; false)`; one `DisplayMode` formula for all action buttons: `If(varBusy || !Connection.Connected; DisplayMode.Disabled; DisplayMode.Edit)`.
- After writing through a flow, `Refresh(<list>)` before reloading; otherwise `ClearCollect` returns the cached old state [B] (PAPPS-20260930-MAC-03).
- Permission and owner checks run in the flow through `x-ms-user-email`, never through an app parameter; the app only shows the result. [B]

## Errors
- Keep `IfError` branches type-compatible: a success branch with `ClearCollect` (table) and an error branch with `Set` (Boolean) give "invalid argument type". End the action or error branch with `Blank()` and keep the error visible through status variables [B] (PAPPS-20260928-MAC-02).
- `IfError(Flow.Run(…); Blank())` swallows the cause; show `FirstError.Message` or write it to a status variable [B] (PAPPS-20261005-MAC-01).
- Empty text: check with `IsBlank(x)` (if needed `IsBlank(x) || x = ""`), never with `Coalesce(x; "") = ""`: `Coalesce` returns Blank for `""`, and `Blank() = ""` is false [B] (PAPPS-20260930-MAC-02).
- Long read-only text: a `TextInput` in `DisplayMode.View` cuts it off without a scroll bar; use a label with `Overflow.Scroll` and a fitting height [B] (PAPPS-20260928-MAC-03).

## Errors only in the published app: the Monitor
Errors that appear only in the published app, only at a cold start or only for other users are proven with the **Power Apps Monitor**, not guessed from formulas [B] (PAPPS-20261007-MAC-02): card "open the published app through Monitor (or 'connect user' for another user), trigger the error, filter the events on it, download them to `inputs/`". The export names control, property and formula. A typical cause: formulas use variables that are set late in `OnVisible` and are empty at the first render; guard the empty state (`If(IsBlank(von) || IsBlank(bis) || bis <= von; ""; …)`) and every division by a variable denominator.

## Other users in a Dataverse environment [B] (PAPPS-20261005-MAC-01)
Outside the default environment every flow call from the app failed for everyone but the creator with `0x80048306` (no read on "Process"); no flow run appeared, the app only showed "not reachable". Before the first test with other users create a security role "<app> app user" with read on **Process** and **Connection reference** (business unit level; the second as a precaution) and assign it to all app users, for many users through a group team with an Entra group. Plan it again when the app moves to another environment.
