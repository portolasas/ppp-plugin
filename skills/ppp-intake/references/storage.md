# Storage of a project

`storage` in `project.json` names where the project data lives (ppp repository `entwurf/ABLAGE.md`). Every project is a git repository on `main`; the plugin itself always comes from GitHub. Options of each command: `ppp <command> --help`.

| storage | remote | after each step | backup | another computer |
|---|---|---|---|---|
| github | origin on github.com | commit and push | the remote | `git pull` |
| local | none | commit | `ppp backup` on request | `ppp backup` there, `ppp restore` here |
| bitbucket | prepared, not tested yet | commit and push | the remote | `git pull` |

## At intake
- **GitHub:** a new private repository with `gh repo create <name> --private --source . --remote origin` after a card, or an existing one with `ppp storage github --remote <url>`. Commit "Intake" and push.
- **Local folder:** no server, no project data on GitHub. The project folder lies outside OneDrive, iCloud Drive, Dropbox and Google Drive (a sync service can break its git history, the only one; `ppp check` warns). Commit "Intake". When `ppp settings` shows no `backupFolder`, ask on one card for a folder outside this computer's disk, such as OneDrive or a network drive, and save it with `ppp settings --backup <folder>`.
- **Bitbucket:** in preparation. Start as local folder and note in `STATE.md` under "Open questions and assumptions to confirm": "Storage: Bitbucket once it is connected".

## Working in a local folder
- Commit after each step as in every project; the history stays in the folder. Session logs stay on this computer: `ppp sessions` skips local projects.
- Back up when the user asks, and when `ppp check` reminds you (last backup older than 7 days with commits after it): offer it on a card, "Back up now (recommended)" or "Later". `ppp backup` writes one checked bundle with the whole history; it refuses uncommitted changes, so commit first. The newest 10 stay; `ppp backup --list` shows them.
- An older state of a file or folder comes from the project's own history: `git log -- <path>`, then `git restore --source <commit> -- <path>`, check it, commit.
- A lost or damaged folder, or a move to another computer: `ppp restore <backup folder>/<prefix> <new folder>` takes the newest backup, a `.bundle` file a chosen one. The new folder is the project from then on: open it as the workspace and run `ppp check`. One folder at a time.

## ZIPs for another computer
`exchange/` stays out of git, because a package can be rebuilt from its commit. A project that is built on one computer and exported or imported on another needs its ZIPs to travel:
- Ask on a decision card, "exchange/ in git (recommended for two computers)" or "ZIPs stay local". Then `ppp storage --exchange git` writes `exchange` into `project.json` and the lines of `.gitignore`; commit both. A new project takes `ppp init … --exchange git`.
- From then on the exports, packages and reports in `exchange/` and `exchange/archive/` are committed and pushed with each step; the work folders `walks/` and `tenant/` stay local.
- A ZIP that lies elsewhere in git moves to `exchange/` with `git mv`; `ppp check` reports it until then.
- Back: `ppp storage --exchange local`, then `git rm -r --cached exchange`.

## Team folder
A team shares a synced folder, such as a SharePoint library: `ppp settings --team <folder> --person <name>` (ppp repository `entwurf/HOME.md`). The work stays in a folder outside it.
- **Share a project** when the user wants it: `ppp team share` answers `CONFIRM FIRST`, which is a decision card with "Share" and "Not now"; then the command with the code it names, and commit `project.json`.
- **A shared local project** backs up into the team folder under the person's name (`ppp backup`). A colleague takes it over with `ppp restore "<team folder>/projects/<prefix>-<id>" <new folder>`. One person works on it at a time: back up before handing over.
- **A shared project with a remote** notes only who works on it and what proved itself; a colleague clones the remote.
- **`ppp check` prints `S team:`** with who else is on the project. An error there means a colleague holds a newer state: show the card the line names before any further work.
- `ppp projects --team` lists the shared projects, who was last on each and how to take one over.

## Switching the storage
- **To GitHub or Bitbucket:** the user creates the empty repository, `ppp storage <github|bitbucket> --remote <url>`, commit `project.json`. Then a card before the first `git push -u origin main`: from then on the whole history lies on that server.
- **To local:** after a card, `ppp storage local` removes the remote. What was pushed stays on the server until the user deletes the repository there.
- **Bitbucket** is known to schema, `ppp check` and `ppp storage`; sign-in, the company's server address and creating the repository are not tested yet. Say so on the card.
