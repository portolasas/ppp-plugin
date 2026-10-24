# SharePoint from flows

List design, field XML and the setup flow are in the skill ppp-sharepoint.

## Lists and items
- Multi-line text columns are unsuitable for emptiness checks in a filter query; keep a dedicated Boolean or choice flag (e.g. `HatFehler`). [B]
- Hyperlink columns come from `Get items` as a URL string; writing an empty string is invalid. Write an object with `Url` and `Description`. [B]
- A required choice column blocks error rows when the value set lacks a neutral value; add one (e.g. `Unbekannt`) before writing error rows. [B]
- Uniqueness on an ID column: backfill first, check idempotency (second run changes nothing), then switch it on. [B]

## REST with "Send an HTTP request to SharePoint"
- The URI starts with fixed text, dynamic parts inline as `@{…}`; an URI that is entirely an expression was rejected on import, and the same form appeared in eight further actions of the workflow: on such an error check every `parameters/uri` of the flow [B, acceptance of the fix open] (PA-20260929-MAC-01). `ppp verify` C10.
- Write: `POST _api/web/lists/getbytitle('<List>')/items(<id>)` with headers `IF-MATCH: *`, `X-HTTP-Method: MERGE`, `Content-Type: application/json;odata=verbose`, body with `__metadata.type = <ListItemEntityTypeFullName>`. [B]
- `ListItemEntityTypeFullName` is specific per list; never guess or copy it. Read it: `GET _api/web/lists/getbytitle('<List>')?$select=ListItemEntityTypeFullName,Id`. [B]
- A wrong or missing item ID gives `…/items()` with HTTP 400, usually a lookup that found nothing. [B]
- JSON body rules (escaping, Booleans): [expressions.md](expressions.md). [B]

## Files
- `Get file content using path` returns a different body per file type; read the shape from the actual run and its `Content-Type`, never from the extension or the action name alone [B] (PA-20260925-MAC-01):
  - `.txt`: a readable string, `@body('<Action>')`;
  - `.vtt` and a Markdown file: an object `{ $content-type, $content }` with Base64, `@base64ToString(body('<Action>')?['$content'])`;
  - `.json` with `Content-Type: application/json`: the JSON object itself; neither decode nor parse it again.
- `Create file` returns `body/Path` relative to the library. [B]
- For SharePoint `executeFlow` take the complete value from "Export › Get flow identifier". [B]

## Graph IDs
- Graph IDs of mails and events are no stable keys; resolve a mail again through `InternetMessageId`. [B]
