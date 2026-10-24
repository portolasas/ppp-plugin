# Error messages

## Message → cause → fix
| Symptom | Cause | Fix |
|---|---|---|
| Import: `WorkflowRunActionInputsInvalidProperty` on `SetVariable` | variable reads itself | compute in `Compose`, then set (C7) |
| Import: `InvalidFlow` on `Append to array variable` | references the same array, also through `length()` | separate counter |
| Import: run-after invalid | `runAfter` names a non-sibling | move the action or chain inside the same scope (C7) |
| Save: `InvalidTemplate` on a reference | referenced action is no runAfter predecessor in the scope path | reorder or reference through an enclosing scope (C13) |
| Save or import: "nested at level 9 which exceeds the maximum nesting limit of 8" | nesting too deep | flatten (C12, [structure.md](structure.md)) |
| Save: `InvalidWorkflowRunAction` | `Terminate` inside a loop | collect errors, terminate after the loop (C10) |
| Import fails, the JSON looks fine | UTF-8 BOM in a workflow JSON | save without BOM (C6) |
| Import rejects an SharePoint HTTP URI | the whole `parameters/uri` is one expression | fixed text first, `@{…}` for dynamic parts (C10) |
| Designer: "'Value' is required" | `SetVariable.value = ""` | sentinel literal |
| `The template function 'padLeft'/'createObject' is not defined` | function missing | replacement in [expressions.md](expressions.md) (C7) |
| Import: `TemplateValidationError` "Unable to parse template language expression 'odata.nextLink'" | a property name starts with `@` | `@@` before the name (C9) |
| Run time: `createArray` "expects a comma separated list of parameters" | `createArray()` without arguments | `json('[]')` (C7) |
| Run time: `json()` … "invalid JSON" | `json()` used as serializer | escape the text in the body |
| SharePoint 400 "Invalid JSON" with `True`/`False` | Boolean through `string()` | `if(<bool>,'true','false')` |
| SharePoint 400 on `…/items()` | lookup found nothing, ID empty | check key or run ID, ensure the registration row |
| `Property selection is not supported on values of type 'String'` | body is a string already, expression uses `?['$content']` | `body('<Action>')` for this file type |
| `replace` expects a string, gets an object | body is an object for this file type (e.g. VTT) | branch per file type |
| `decodeBase64`/`base64ToString` expects a string, gets an object | body is `{ $content-type, $content }` | `@base64ToString(body('<Action>')?['$content'])` |
| `substring`: start index must be less than the length | empty text | `substring(concat(x,' '),0,min(length(x),n))` |
| Condition shows `equals("","")` after editing | was stored as expression string | structured conditions only (C8) |
| Condition value becomes `@@…` | plain-text `@` in a standard condition | expression tab, without `@` |
| Filter query ignored or invalid | whole field built as one expression | OData text plus `@{…}` for the dynamic part (C10) |
| Parent waits, child starts again and again | child failure plus retries [O] | cancel the concrete run, check retry settings |
| Flow checker fine, save fails | checker misses designer required fields | always save and reopen |
| `Update item` rejects a field from the package | internal column name differs or connector schema stale | re-bind in the designer, pass required fields |
| Prompt output with missing fields, wrong casing, object instead of array | model follows structured output only partly | skill ppp-copilot-studio |

## Checks of `ppp verify`
| Check | What | Level |
|---|---|---|
| C1 | file set as in the base (export or last package) | error |
| C2/C3 | every JSON and XML parsable | error |
| C4 | changed files; with `--allowed` only released ones | info / error |
| C5 | version raised | error |
| C6 | no BOM in workflow JSON; BOM state and line endings unchanged | error / warning |
| C7 | unique action names, runAfter on siblings, SetVariable/Append with value and without self reference, `json(` and `string(<bool>)` in bodies, missing functions, `createArray()`, retry policies | error / warning |
| C8 | conditions structured | error (new) / warning (existing) |
| C9 | expression syntax: empty arguments, brackets, strings, unclosed `@{`; property names with a leading `@` | error |
| C10 | Terminate in loops; URI, filter and order-by fields made of one expression | error / warning |
| C11 | references to unknown actions or variables, `items()` outside its loop, reads from a foreign loop | error / warning |
| C12 | nesting depth at most 8 | error |
| C13 | every referenced action on a runAfter or scope path | error |
| C14 | no app in the package (only with `--with-apps`) | error |
