# The app and the solution

- An app lives outside the main solution and comes into it only for a move to test or production (ARBEITSWEISE A-7, skill ppp-golive). Screens reach it by "paste code", not by a package.
- **Save and publish the app before exporting a solution that contains it**: three exports in a row held the old app state although the change seemed published; only after publishing again was it in the export [B]. Check it through `Other/Customizations.xml` (in the ZIP `customizations.xml`) › `<CanvasApp>` › `<AppVersion>`, the UTC time stamp of the saved state, which must be newer than the last change; in the unpacked solution `CanvasApps/<name>.meta.xml`.
- The app calls exactly one flow per action through its workflow ID (`workflowEntityId` in the `.msapp`, `Properties.json` or `References/DataSources.json`); with duplicate flows of the same name in the export, build the one the app uses (SOL-20261009-MAC-01, skill ppp-package).
