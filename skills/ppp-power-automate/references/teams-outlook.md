# Teams, Outlook, To Do, Graph

- **Adaptive cards in Teams** know no own hex colours, only host styles: `default`, `accent`, `good`, `warning`, `attention`, `emphasis`. Mapping: good = success, attention = error, warning = warning, accent = information [B, schema limit].
- Images in cards need a URL the card client can read, e.g. a SharePoint library readable for the users [O].
- **Outlook category colours**: the palette of the new Outlook is not ordered by the Graph presets `preset0` to `preset24`, and the colour names do not always match the Graph names [B] (PAPPS-20260928-MAC-05). Map them like this: read the existing categories through Graph `masterCategories`, link the field `color` to a visible colour sample, never derive it from the position or a similar name.
- Graph `PATCH` on `displayName` of an Outlook master category returned 200, but the name stayed; `color` could be changed by `PATCH`. [B]
- Graph IDs of mails and events are no stable keys; resolve a mail again through `InternetMessageId`. [B]
- **Microsoft To Do (Business)**, `ListToDosByFolderV2`: the response is a bare array, without `value`. Pagination on the action fails every run with `InvalidPageResponse` [B] (PA-20261115-WIN-03). It returns 10 tasks unless `top` asks for more (up to 999) [D]: read a tracked task outside them by its ID (`GetToDoV3`); only a 404 there means deleted. A test replica answers with the bare array too.
- Teams transcripts: see [triggers.md](triggers.md).
- Mail templates and adaptive cards of a project live in `components/power-automate/templates/`.
