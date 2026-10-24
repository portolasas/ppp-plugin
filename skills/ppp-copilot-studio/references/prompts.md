# Prompts

## In a flow
- Flow action for own prompts: `aibuilderpredict_customprompt`. The raw answer is at `@body('<Action>')?['responsev2']?['predictionOutput']?['text']`. [B]
- Each input variable may occur **only once** in the prompt text. [B]
- When creating an input no sample values can be stored. [B][V]

## Structured output
- Arrays of primitive types are not supported; use minimal object arrays such as `[{ "value": "task" }]`. [B]
- Structured output alone did not keep reasoning models in the schema [B]: required fields missing or renamed, decimal instead of integer, object instead of a one-element array, wrong enum spelling.
- What helped [B]: configure structured output **and** append the complete schema verbatim to the prompt text (heading "Binding output schema"), and repeat explicitly: arrays also for 0 or 1 element, exact enum spelling, integer ranges, required fields.
- When a value belongs to the enum of another field (e.g. route versus intent), say so in the prompt. [B]
- A complex output changed through solution XML and imported kept only one top-level field; create complex outputs in the real Prompt Builder. [B]

## Prompt text
- State deterministic constraints numerically, e.g. "next `start` = previous `end` + 1; no gaps, no overlaps; give remainders to a neighbour; check the numbers yourself at the end". [B]
- Low temperature for extraction and classification (0–0.2). [B]
- Output JSON only, no prose, no code fences. [B]

## Validation in the flow
- `Parse JSON` with a strict schema, then the business invariants in a validation scope (coverage, IDs, enums, rules across fields). [B]
- A violation sets a visible error status; the raw answer is stored JSON-escaped. [B]
- At most one retry, and only **before** the first write; prompt actions get `retryPolicy = none` so the call limit holds. [B] (`ppp verify --retry-none`)
