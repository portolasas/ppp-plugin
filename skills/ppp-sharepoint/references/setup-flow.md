# Setup flow

Citizen-developer tenants usually lack PnP and site scripts. Lists are therefore created by one manual flow `<prefix>_Setup` that can run any number of times (pattern ASUM_Setup: imported and run twice in the tenant, 2026-10-08 [B]).

## `components/sharepoint/schema.json`
The keys stay those of the former `listen_definition.json` (German keys, kept so that existing definitions and flows carry over):
```json
{
  "schemaVersion": "1.0",
  "optionen": 25,
  "listen": [
    {"titel": "XY_Rollen", "beschreibung": "Role per person (Title = e-mail in lower case)", "basis": 100,
     "titelFeld": {"Indexed": true, "EnforceUniqueValues": true},
     "felder": [
       {"name": "Rolle", "schemaXml": "<Field Name=\"Rolle\" StaticName=\"Rolle\" DisplayName=\"Rolle\" Type=\"Choice\" Format=\"Dropdown\"><CHOICES><CHOICE>Admin</CHOICE><CHOICE>Leser</CHOICE></CHOICES></Field>",
        "werte": ["Admin", "Leser"]},
       {"name": "Aktiv", "schemaXml": "<Field Name=\"Aktiv\" StaticName=\"Aktiv\" DisplayName=\"Aktiv\" Type=\"Boolean\"><Default>1</Default></Field>"}]}
  ],
  "daten": [{"liste": "XY_Einstellungen", "schluessel": "Title", "items": [{"Title": "Grenze", "Wert": "5"}]}],
  "setup": {"laufListe": "XY_Laeufe",
            "versionEinstellung": {"liste": "XY_Einstellungen", "titel": "SchemaVersion"},
            "ersterAdmin": {"liste": "XY_Rollen", "rolle": "Admin"}}
}
```
- `basis`: 100 list, 101 library. `titelFeld`: index and uniqueness of Title (only raised, never lowered).
- `werte` on a choice field: the values an **existing** field must have; missing ones are added, existing ones stay in their order. Keep `werte` equal to the CHOICES.
- `daten`: start values, inserted only for keys that are missing.
- `setup` (each part optional): `laufListe` with the fields Art, Status, Modus, Start, Ende, Ergebnis, Meldung gets one entry per run; `versionEinstellung` (fields Wert, Beschreibung) receives the `schemaVersion`; `ersterAdmin` (fields Rolle, Aktiv) enters the caller as first admin while no active admin exists.
- Large master data from a migration (hundreds of rows) is not loaded by the setup flow; decide per project how it gets in (separate flow reading files, or an import by the user).

`ppp schema` checks the file: names, Name/StaticName, types, CHOICES and `werte`, prefix, start values against the fields, the fields the setup parts need.

## Build the flow
1. Scaffold by the user (tenant-step card): instant flow `<prefix>_Setup` with a text input **Phase**, one "Send an HTTP request to SharePoint" whose Site Address is the environment variable of the site, and "Respond to a PowerApp or flow" with one text output **ergebnis**. Export, `ppp unpack`.
2. `ppp setupflow` writes the logic from `schema.json` into the scaffold; every other byte of the file stays. It prints the writing actions; check with `ppp verify --retry-none <list>`.
3. Test it locally with `wdl_sim.Site` (list and field administration in the simulator) in `tests/` via `ppp run`.

## What the flow does
- Phase **Schema**: reads all list titles once; per list (Try/Catch, the others continue): creates the list if missing, raises the Title index, creates missing fields with `createfieldasxml`, adds missing choice values; result line `<list>: neu=<n>`. Then the schema version setting.
- Phase **Daten**: per start-value block reads `ListItemEntityTypeFullName` (never guessed) and the existing keys, inserts only missing items (parallelism 5); result `<list>: vorhanden=<a>, neu=<n>`. Then the first admin.
- **Alles** = Schema, then Daten. Another phase value: error, no write at all.
- Never changes or deletes fields, lists or items (exception: the version setting). The response `ergebnis` is `OK: …` or `Fehler: …` on every path; with errors the run ends Failed afterwards.

## Tests
| Test | Expectation |
|---|---|
| Schema | lists and fields with type, choice values, indexes and uniqueness as defined; second run creates nothing |
| Data | counts as expected; 10 samples field-equal with the source; second run adds 0 |
| Permissions | a user without write rights reads in app and list and cannot edit in the list; the flow writes |
| Threshold | filtered queries on the largest list run without delegation or threshold errors |
