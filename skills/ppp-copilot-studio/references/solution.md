# Agents and prompts in the solution export

- Agent components lie under `botcomponents/<schema>.<kind>.<name>/` with a `data` file (YAML, e.g. `kind: TaskDialog` for prompt actions) and `botcomponent.xml`; the bot itself under `bots/<schema>/` with `bot.xml` and `configuration.json`. [B] `ppp unpack` lists them.
- Packages of flows leave these files byte-identical; changes to agents and prompts are made in Copilot Studio and Prompt Builder. [B]
- Microsoft's VS Code extension "Copilot Studio" (clone, edit and apply agent YAML) is an alternative, not tried here [O].
