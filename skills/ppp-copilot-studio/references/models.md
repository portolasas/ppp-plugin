# Models [V]

The choice depends on the tenant, the licence and the data policy; check the visible options before every choice.

- Seen in one tenant (September 2026): Prompt Builder offered GPT-4.1 mini, GPT-4.1, GPT-5 chat, GPT-5 reasoning, Claude Sonnet 4.6 and Claude Opus 4.6 (experimental); the agent configuration showed more (e.g. Claude Opus 4.8, GPT-5.5 chat).

| Task | Model class | Experience |
|---|---|---|
| fast classification with strict JSON (e.g. mail triage) | GPT-4.1 | stable in production with structured output [B] |
| extraction or segmentation with long context and a complex schema | GPT-5 reasoning | slower; needs the schema repeated in the prompt text [B] |
| consolidation of long pages | a strong model (Claude Opus class) | planned, not confirmed [O] |

- Claude models answered in the test hub inside code fences; the hub's JSON evaluation was unreliable for them. [B]
- Billing and capacity (Copilot credits) are clarified with the Power Platform admin. [O]
