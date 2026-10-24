# REST write patterns ("Send an HTTP request to SharePoint")

- **Update an item** [B]: `POST _api/web/lists/getbytitle('<List>')/items(<id>)` with headers `IF-MATCH: *`, `X-HTTP-Method: MERGE`, `Content-Type: application/json;odata=verbose`, and `__metadata.type = <ListItemEntityTypeFullName>` in the body. Requests carry `Accept: application/json;odata=verbose` (or `odata=nometadata`, which returns the item without `d` and `__metadata`).
- The `Accept` format decides the shape of the answer: with `odata=verbose` the item sits under `d`, so a parser that read `Id` at the top level got an empty ID and `int()` failed. Ask for `odata=nometadata` to read flat, or read `d`; HTTP mocks in tests return the requested format [B] (PA-20261021-WIN-01).
- **`ListItemEntityTypeFullName` is specific per list**; never guess it or take it from another list. Read: `GET _api/web/lists/getbytitle('<List>')?$select=ListItemEntityTypeFullName,Id`. [B]
- A wrong or missing item ID gives `…/items()` with HTTP 400; mostly a lookup found nothing. [B]
- **Optimistic lock**: valid states are switched through **one** pointer in a header item, set in one MERGE with `IF-MATCH: <ETag>`; HTTP 412 means conflict, nothing becomes visible. With several writers always `IF-MATCH: <ETag>`, never `*`. [B]
- The ETag is in `d.__metadata.etag` with `odata=verbose`, also directly in the **response of the POST** that created the item: `body('<Create>')?['d']?['__metadata']?['etag']`; no second read [B] (SP-20260930-MAC-01).
- With `odata=minimalmetadata` the item carries its ETag as `odata.etag`; guards and `IF-MATCH` that read only `@odata.etag` found none and stopped before the first write. Read both spellings, pass the token unchanged, never fall back to `*` [B] (PA-20261022-WIN-01).
- The run ID `workflow()['run']['name']` belongs into the titles of rows a run writes, so retries never collide with leftovers; a cleanup flow removes rows of runs that never committed.
- In URIs fixed text first, dynamic parts as `@{…}`; no `$filter` built as one expression (skill ppp-power-automate).
- Times: SharePoint stores date and time in UTC, REST returns UTC ISO strings. [B]
- Test entries are moved to the recycle bin (`…/items(<id>)/recycle()`), not deleted. [B]
