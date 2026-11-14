# Custom connectors

A custom connector wraps an API for the flows: an OpenAPI 2.0 definition, optionally a C# script that rewrites requests and responses, and a connection of its own.

## Files
`components/power-automate/connectors/<name>/` holds the connector as the wizard takes it: `apiDefinition.swagger.json`, `script.csx` when it has code, the test bodies and a `README.md` with host, authentication and operations. `ppp check` accepts one folder per connector there (GEN-20261110-MAC-02).

## Before planning one
- Ask on the first card whether the environment's DLP policy puts the connector's host into the same group as the other connectors of the flow. A custom connector is classified by a host URL pattern, and a flow that mixes the business and the non-business group cannot be saved; the HTTP action can sit in another group than a custom connector for the same host. [B] (PA-20261110-MAC-02)
- When the groups differ, draft the request to the DLP admin at once, with the host pattern and the connectors of the flow. Two flows chained across the groups break the same policy: wait for the approval.
- Until the approval a flow may call the API with the HTTP action, when the policy allows that pairing and the password stays out of the definition and the exports: read at run time from a restricted list item or a secret environment variable. [B]

## Creating it
- "Code enabled" can fail with `failed to provision compute for custom code … FindAndAssignFunctionApp unable to find unassigned function app`. Create the connector with code disabled and switch the code on later with "Update connector" [B]; the cause, regional capacity for the first code connector of an environment, is [O].
