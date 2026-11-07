# Roles

A guide shows every action from the session of the role that does it, with that role's permissions, never from a developer account that sees more. So one walk per role and task:
```json
"role": {"name": "Shift lead", "identity": {"control": "lblRole", "equals": "Shift lead"}}
```
- `identity` names a control that shows who is signed in or which role the app assigned, with `equals` or `contains`. The run stops without a picture when it does not match; single sign-on may quietly log in the user's own account. If the app shows no such control, add one to the screens first, in a package.
- Each role has its own browser profile `~/.ppp/edge-profile-<role>`. On its first run the walk waits on the sign-in page (SKILL.md, section 1): the user signs in there with the role's test account. Passwords stay with the user.
- Without a test account per role: decision card with what is possible, for example a list entry that assigns the role to the user's own account while the walk runs, with the rules of SKILL.md, section 3.
- A click on a control the role lacks stops the run, as does a disabled one. That is the check that the chapter fits the role; a step the role cannot do does not belong in its chapter, or it reveals a defect in the permissions.
- Add `expect` with `absent` for what this role must not see, from `specs/`, so the walk also tests the permissions. A check that runs in a flow shows only by doing the step: follow SKILL.md, section 3.
- `ppp guide <walks> --role "<name>"` builds the guide of one role from its walks ([ppp-docs/references/guide.md](../../ppp-docs/references/guide.md)).
- A guide for several roles takes one chat per role: at the end of a role save the state, then the start prompt for the next role as a code block in the chat and below it a stopping-point card with "New chat (recommended)".
