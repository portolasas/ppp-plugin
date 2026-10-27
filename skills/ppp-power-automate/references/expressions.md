# Expressions (workflow definition language)

## Functions that do not exist or fail [B]
| Function | Replacement |
|---|---|
| `createObject()` | `json('{}')` with `addProperty(...)` or `setProperty(...)` |
| `padLeft()` | three digits (`S001`): `@substring(concat('000',string(<n>)),sub(length(concat('000',string(<n>))),3),3)` |
| `createArray()` without arguments: imports, then fails at run time ("expects a comma separated list of parameters") (PA-20261024-WIN-02) | `json('[]')` |

`ppp verify` C7 reports all three; `wdl_sim` fails on `createArray()` as the tenant does.

## Building JSON
- `json()` **parses** valid JSON text; it is no serializer. `json('Aktuelle Stände')` fails at run time. [B]
- In REST and HTTP JSON bodies put text values in quotes and escape backslash, quote, CR and LF [B]:
  `"Title": "@{replace(replace(replace(replace(<text>,'\','\\'),'"','\"'),decodeUriComponent('%0D'),'\r'),decodeUriComponent('%0A'),'\n')}"`
- Booleans: `True`/`False` from `string(or(...))` is invalid JSON, SharePoint answers 400 "Invalid JSON". Use `@{if(or(...),'true','false')}` without quotes. [B]
- Real parsing with `Parse JSON` and a strict schema. [B]
- A property name that starts with `@` is read as an expression, in schemas and bodies too: `@odata.nextLink` as a Parse JSON schema key failed the import with `TemplateValidationError` ("Unable to parse template language expression 'odata.nextLink'"). Write `@@odata.nextLink`; reading a response stays `?['@odata.nextLink']` [B] (PA-20261024-WIN-01). `ppp verify` C9 checks property names too.
- `setProperty` rejects property names containing `.`, `[` or `]`, at run time only: a key built as `concat(<list>,'.',<field>)` imported and failed the run ("The provided property name … has these invalid characters '.'"). Nest the objects: `setProperty(<o>,<list>,setProperty(<inner>,<field>,<value>))` [B] (PA-20261026-WIN-01). `wdl_sim` applies the rule to `setProperty` and `addProperty`, `ppp verify` C9 to literal names.
- Build expressions in files or generators, never through shell or Python string literals: quotes get lost (`replace(x,,'')` once broke a whole package). [B] `ppp verify` C9 checks the syntax.

## Variables
- `Set variable` must not read its own variable in the value (`WorkflowRunActionInputsInvalidProperty` on import). Compute in a `Compose`, then set. [B]
- `Append to array variable` must not reference the same array, not even through `length(<array>)` (`InvalidFlow`). Keep a separate counter and raise it before the append. [B]
- `Set variable` with the empty literal `""` imports, but the designer refuses to save ("'Value' is required"). `@''` could be published once and was empty again on the next publish [V] (PA-20260925-MAC-03). Robust: a non-empty **sentinel literal** such as `__NO_ERROR__`, compared with equals or not equals. [B]

## Reading outputs
- `Get item`: `@outputs('<Action>')?['body/<Field>']` · choice: `…?['body/<Field>/Value']` · in loops `@item()?['<Field>']?['Value']` · Yes/No without `/Value`. [B]
- Child-flow result: `@body('<Run a Child Flow>')?['<field>']`. [B]
- A condition that refers to an action that did not run gets `null`. [B]
- Inputs of a manual trigger are internally `text`, `text_1`, …; the mapping is in the code view. Multi-select or array inputs may need `@first(triggerBody()?['text'])`. [B]

## Text
- `substring(text, 0, n)` fails on empty text, even with n = 0: the start index must be below the text length. Safe: `substring(concat(x,' '),0,min(length(x),n))`. [B] (ASUM, 2026-10-08)
- `startsWith` and `endsWith` expect text: an object fails the run ("expects its first parameter to be of type string. The provided value is of type 'Object'"). Read the text property first, e.g. `?['Url']` of a hyperlink value from REST [B] (PA-20261026-WIN-02). `wdl_sim` fails the same way.
- VTT timing line: `trim()` the part after `-->` before cutting off the cue settings, otherwise `int()` fails on the leading blank [B]:
  `@first(split(trim(last(split(outputs('<Compose_TimingLine>'),'-->'))),' '))`

## Performance
- A sequential `Apply to each` over about 180 entries with shared variables took about 160 s; four indexed `Select` stages and one `Set variable` took under 3 s. Prefer pipelines of `Select` and `Filter array` over loops with appends. [B]
