---
name: ppp-copilot-studio
description: Copilot Studio and AI Builder prompts - prompts called from flows, structured output, prompt text rules, validation, model choice, test hub, agents in a solution export. Use before building, changing or testing a prompt or an agent.
---

# Copilot Studio and prompts

Status per statement: **[B]** observed in the tenant, **[D]** documentation, **[O]** open, **[V]** version-dependent. Copilot Studio is used in its classic and its new experience (ANFORDERUNGEN T7).

## Always
1. Prompt text, inputs and structured output are set **directly in Prompt Builder** from local sources in `components/copilot-studio/<name>/`: `PROMPT.md`, `SCHEMA.json`, `TESTS.csv`; never through solution XML. The user pastes the complete text block from a card. [B]
2. The flow validates every prompt output strictly; the model output is never trusted as it is. [B]
3. After a prompt change: save, **publish**, then repeat the flow test. [B]

## References
| Topic | File |
|---|---|
| Prompts in flows, inputs, structured output, prompt text, validation | [references/prompts.md](references/prompts.md) |
| Model choice | [references/models.md](references/models.md) |
| Test hub, test chat, test data | [references/testing.md](references/testing.md) |
| Agents and prompts in a solution export | [references/solution.md](references/solution.md) |
