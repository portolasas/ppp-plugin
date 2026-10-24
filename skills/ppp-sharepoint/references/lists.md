# Designing lists

## Columns
- **Internal names** without umlauts, spaces or special characters. The first name at creation becomes the internal name and cannot change; the display name can. [D] `ppp schema` checks the names.
- **Relations through text or number keys** instead of lookup or person columns when apps or flows filter on them (delegation, threshold, lookup limit per view). [D]
- **JSON snapshots** in multi-line **plain text** columns (`RichText="FALSE"`), compact keys, well below the limit of about 63,000 characters. [D]
- Multi-line text is unsuitable for emptiness checks in a filter query; keep a Yes/No or choice flag (e.g. `HatFehler`). [B]
- **Hyperlink columns** come from `Get items` as a URL string; writing an empty string is invalid, write an object with `Url` and `Description`. [B]
- **Required choice columns** need a neutral value (e.g. `Unbekannt`), otherwise error rows cannot be written; add it before error rows appear. [B]
- **Switching uniqueness on**: backfill existing data, check idempotency (a second run changes nothing), then "enforce unique values". [B]

## Field XML for `CreateFieldAsXml`
| Type | XML core | Note |
|---|---|---|
| Text | `Type="Text" MaxLength="255"` | key: `Indexed="TRUE"`, `EnforceUniqueValues="TRUE"` |
| Multi-line, plain text | `Type="Note" RichText="FALSE" NumLines="6"` | JSON, logs; not filterable |
| Number | `Type="Number" Decimals="0"` | |
| Yes/No | `Type="Boolean"` with `<Default>0</Default>` | |
| Date and time | `Type="DateTime" Format="DateTime"` | stored in UTC |
| Choice | `Type="Choice"` with `<CHOICES><CHOICE>…</CHOICE></CHOICES>` | plan a neutral value |

`Name` and `StaticName` hold the internal name, `DisplayName` the label. `Options = 25` is AddToDefaultContentType (1) + AddFieldInternalNameHint (8) + AddFieldToDefaultView (16). `EnforceUniqueValues` requires `Indexed`. [D]

## Indexes, threshold
- Create indexes **before** importing data. In lists that can grow beyond 5,000 items every column that apps or flows filter or sort on gets an index; at most 20 indexes per list. [D]
- The key column (usually Title) is unique and indexed; it is the idempotency key of inserts.
- Estimate the growth per list (start and per year) in the inventory README; above 5,000 it needs an index and a test.

## Permissions
- Users get **read** rights; writes run only through flows whose connection account can edit. Never give users edit rights "for now": edits in the list UI bypass every check. [B]
- Moving from the creator's account to a technical account is a step of its own: switch the connection references in the solution and test the writes again.

## Evidence for schema and counts
- Cheapest: the list export "CSV with schema"; its first line (`ListSchema=`) holds internal names, types, required, index, uniqueness and choice values, the rows give the counts. [B]
- REST in the browser only for what the export lacks (`ListItemEntityTypeFullName`, list GUID): give the complete URL and say "open in the browser, signed in to SharePoint", e.g. `…/_api/web/lists/getbytitle('<List>')/fields?$select=Title,InternalName,TypeAsString,Required,Indexed&$filter=Hidden eq false`. Flows that write by REST read `ListItemEntityTypeFullName` themselves at run time.
- IDs per environment (site URL, list GUIDs) go to `environments/<environment>.json`.
