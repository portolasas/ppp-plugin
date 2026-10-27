---
name: ppp-sessions
description: Upload of this computer's session logs of ppp projects to the user's private sessions repository, where a learning session evaluates them to improve ppp. Use when the user asks to upload, save or share sessions or chats.
---

# Upload sessions

`ppp sessions` copies the Copilot session logs of ppp projects (working folder with `project.json`) that changed since the last upload of this computer into the clone of the sessions repository, commits and pushes. Lock files and the agent's scratch folder `files/` stay behind.

1. Run `ppp sessions`. It lists each session with time, ID and project, then reports the push or "nothing new to push".
2. When it reports that no sessions repository is set: ask on one card for the folder of the clone, or for the URL of the repository; clone a URL with `git clone <url>` in the folder that holds the projects. Save the folder with `ppp settings --sessions <folder>` and run `ppp sessions` again. The repository stays private: the logs hold everything the agent read and wrote, project data included.
3. When git fails (network, sign-in), show its message. The time of the last upload advances only after a push, so the next upload takes the same sessions.

`--since <YYYY-MM-DD>` takes older sessions again; `--dry-run` only lists them.

Done when `ppp sessions` reported the push or "nothing new to push" and the user read in one line how many sessions of which projects went up. The current session goes up in its state so far; its later turns come with the next upload.
