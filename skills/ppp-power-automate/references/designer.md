# New designer

## Conditions
- **Only the structured form is designer-safe** [B] (PA-20260926-MAC-01). A condition stored as an expression string (`"expression": "@and(...)"`, typically from a package) shows in the code view but not in the condition editor. Editing it there leaves `equals("","")`, which is always true: errors then pass silently as success.
  - Write `"expression": {"and": [{"equals": ["@<left>", "<right>"]}, {"not": {...}}]}`; groups and `or` are allowed.
  - A function without operator (`empty()`): left `@empty(...)`, operator `equals`, right `true`.
  - Existing string conditions: leave them alone in the designer and convert them in the next package (`ppp verify` C8: new or changed ones are errors, existing ones warnings).
- Standard conditions have no usable advanced mode; describe them to the user as three lines: left value, operator, right value. [B][V]
- An expression on the left goes into the fx editor without the leading `@`. Complex Boolean logic: left the expression, operator "is equal to", right the expression `true`. [B]
- Plain text with a leading `@` in a standard condition is stored as `@@…`; never paste `@and(...)` into a literal box. [B]
- After saving, open the condition again and check it. [B]

## Text, OData, URI and sort fields
- `Filter array` and `Select` may be written in advanced or text mode. [B]
- Filter, URI and order-by fields: the fixed OData text in plain text, only the dynamic part as an expression; the expression must not form the whole field (`ppp verify` C10) [B] (PA-20260929-MAC-01).
  Right: `LaufId eq '@{triggerBody()?['text']}'` · wrong: `@concat('LaufId eq ''',…,'''')`

## Scaffolds and placeholders
- A new instant flow cannot be saved with the trigger alone; add a temporary `Compose`. [B]
- Connector metadata (dataset and table IDs, operation schema, paths of header and body parameters) comes from a placeholder action the designer saved, plus a fresh export. An empty body `{}` disappears on export and proves nothing; use a non-empty dummy body. [B]
- Placeholder flows stay off and write no data. [B]
- Child-flow bindings (`host.workflowReferenceName`) are never written by hand. One designer-saved "Run a Child Flow" per child flow is enough as template for every parent flow in the same solution: copy it, replace only `inputs.body`, keep the reference, set `retryPolicy` none. New child flows: let the user add a placeholder call in the same flow (card), then take it from the export. Tell call kinds apart by the body keys (`number`, `text`, `text_1` …) [B] (PA-20261009-MAC-01).

## Update item
- Fields added to `Update item` through solution JSON can be rejected ("item/<field> not in stored operation schema") [B]. Then: check the real internal column name, re-bind the action in the designer, pass every required column with its current value.
- Only when no safe partial update exists: "Send an HTTP request to SharePoint" with REST MERGE ([sharepoint-connector.md](sharepoint-connector.md)). [B]

## Saving, checking, switching
- The code view is called **Code view** in the tenant (formerly "Peek code"); it shows the stored definition and is the evidence for internal names and stored values. [B]
- Flow checker "No errors found" does not guarantee that the designer can save; save once and reopen as proof. [B]
- A green local check does not replace the designer save test (PA-20261012-MAC-01).
- The on/off state after an import does not follow the package (`StateCode`). [B]
- Switching a flow off does not stop runs in progress; cancel the concrete run in the run history. [B]
- The new designer stores `runAfter` states in upper case (`SUCCEEDED`, `FAILED`, `SKIPPED`, `TIMEDOUT`), older and package-built actions as `Succeeded`; one export can mix both. The runtime accepts both; scripts and simulators compare case-insensitively. Runtime values (`result()`, `actions()?['status']`) stay `Succeeded`/`Failed`. [B]
