---
name: ppp-golive
description: Completion and operation - full test, move to the test or production environment, go-live, hypercare and maintenance. Use when all planned packages are done, before a move to another environment, or after go-live when fixes come in.
---

# Go-live and operation

## 1. Full test
Until now only critical scenarios were tested. Now every scenario of `specs/` is tested once: a test plan in `tests/test-plan.md` (scenario, role, expected values, result), then one card per scenario or per group the user can run in one go. Deviations become packages (ppp-package) or diagnoses (ppp-diagnose).

Done when every scenario has a result and every deviation has a decision.

## 2. Move to test or production
Environments: citizen development, an own test environment, production through the governance process of the company.
1. **IDs per environment** in `environments/<environment>.json`: site URLs, list IDs, connection references, values of environment variables. Nothing environment-specific stays fixed in a flow; a fixed site URL becomes an environment variable in a package first.
2. **Package with apps**: for the move the app comes into the solution (card: Solutions › main solution › Add existing › App), fresh export, `ppp unpack`, then `ppp pack --solution <main solution> --version <next> --with-apps --label <environment>`.
3. **Import card** for the target environment: connections, values of the environment variables from `environments/<environment>.json`, then the setup flow with phase Schema (and Daten, if start values are needed).
4. For production follow the governance process; ppp prepares the documents it asks for, the user submits them.
5. After the move, ask on a decision card whether the app stays in the main solution (every later package then needs `--with-apps` and carries the app from the last export, so changes in Studio must be exported first) or leaves it again; record the answer with `ppp new decision`.

## 3. Go-live and hypercare
Handbook and training ready (ppp-docs). During hypercare the user reports errors; diagnose with exports (ppp-diagnose). Small fixes the user makes by hand are noted in `STATE.md` and rebuilt in the next package; everything else is a package.

## 4. Maintenance
Maintenance runs through the same package cycle. Before the first package after a longer break: a fresh export and `ppp unpack`, so that manual changes in the tenant show up in the diff.
