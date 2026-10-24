# Triggers and environment variables

## Power Apps V2 and manual trigger
- `@triggerOutputs()?['headers']?['x-ms-user-email']` gives the caller's UPN, also on a manual test in the designer ("Test › Manually") and on a manual trigger [B] (PA-20260927-MAC-01, PA-20260930-MAC-01; ASUM 2026-10-08).
- Permission and owner checks belong server-side into the flow, through this header, never into an app parameter. [B]
- Test flows with a role check in the designer first (input as text) before the app calls them; this saves a paste cycle in the app. Negative cases (another role) still need a second account through the app. [B]

## Environment variables in the definition [B] (PA-20260927-MAC-01)
- In the flow definition: `parameters['<display name> (<schema name>)']` with `type: String`, `metadata.schemaName` and the current value as `defaultValue`; referenced as `@parameters('<display name> (<schema name>)')`.
- Take the form over by letting the designer reference the variable once in the scaffold and exporting.
- Values are not packed: without `environmentvariablevalues.json` in the package the existing values stay on import.
- A value changed in the UI took effect after switching the flow off and on [B]; whether it works without that is [O].
- A site address that should move between environments is an environment variable, not fixed text (ANFORDERUNGEN T8).

## SharePoint triggers
- Notifications only on a real change [B] (PA-20260927-MAC-02): trigger condition on the target status and a set key, plus `Get changes for an item or a file (properties only)` with the trigger window tokens; the side effect (e.g. a Teams card) runs only when `ColumnHasChanged` holds for the relevant key. This prevents duplicates on later edits.
- "When a file is created (properties only)" (`GetOnNewFileItems`) gives `ID`, `{IsFolder}`, `{Path}`, `{FullPath}`, `{FilenameWithExtension}`, `{Identifier}`, `{Link}`. [B]
  - `{Identifier}` is the connector's file ID (for `Move file`), `{DriveItemId}` a Graph ID; neither is the SharePoint `File.UniqueId`, which comes by REST through the list ID and the trigger `ID`. [B]
  - Creating folders in the watched folder or moving files into it can trigger the flow again; a trigger condition "files only, no folders, direct level only" prevents it. [B]
- Raw trigger outputs contain personal data and short-lived URLs with tokens; document field names only. [B]

## Teams transcripts
- "When a transcript is available" fired although `Get meeting transcript content` failed with "Speaker-attributed transcript content is disabled for this tenant"; the trigger does not reveal the tenant block [B] (PA-20260929-MAC-03). Before planning an automatic transcript path run a probe with both steps in a scaffold flow; if blocked, plan a manual upload (VTT, TXT).
