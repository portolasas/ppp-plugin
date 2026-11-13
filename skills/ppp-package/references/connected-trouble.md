# Connected project: when something does not run smoothly

The ordinary way: [connected.md](connected.md). Here: refusals, drift, a failed import, pac that does not get through, a restore.

## Refusals
- `ppp export` refuses uncommitted changes in `solution/<Name>/`, `--force` too: commit them (the version `ppp pack` raised too). It refuses committed work the tenant lacks (commits since the last export, a packed, unimported version). `--force` replaces that committed work (it stays in git) only after a decision card.
- `ppp import` refuses: uncommitted changes in `solution/<Name>/`; a package packed before the last export; a version whose import failed, repacked too (`ppp pack --version <next>`).

## Drift
`DRIFT:` means the tenant differs from the base; nothing was imported.
- **Drift lines**: `DRIFT:` and `ppp export --compare` (changes nothing) list under the first line per differing file the differing lines (`-` the project's base, `+` the tenant; a note when only their order differs). The card shows files and lines. If only `Other/Customizations.xml` or `Other/Solution.xml` differs and nobody changed the tenant, the server may have rewritten the file: the lines decide whether it is a manual change; the card stays.
- **Take drift over**: commit the work, `ppp export --force`, rebuild the work on the tenant's state (`git cherry-pick` its build commits or run its generators again), `ppp verify`, `ppp pack --version <next>`, `ppp import`. The package packed before is refused after the takeover: packing anew is a must.

## Failed import
`FAILED:` uses the ZIP and its version up. `ppp tenant --log` gives the record's error texts (none after the 30 minutes). Find the cause (skills ppp-diagnose, ppp-power-automate `references/errors.md`), fix it, `ppp verify`, `ppp pack --version <next>`, `ppp import`. The work in the project stays; `ppp export` does not replace it (`ppp export --compare` shows the tenant's state).

Done when the next import answers `IMPORTED:`.

## When pac does not get through
`ERROR: <KIND>:` below; a refused check is `ERROR:` without a kind, with the next step. The project stays connected.

| Kind | Meaning | You |
|---|---|---|
| `AUTH` | pac is not signed in here | Card, as offline; the user signs in (`pac auth create`), named once |
| `DENIED` | The account may not do this in the environment | Card, as offline |
| `SYNTAX` | pac takes the call differently than ppp expects | Card, as offline; lesson proposal |
| `TIMEOUT` | No answer in time | Once more; then a card, as offline |
| `BUSY` | Another import of this solution runs | Wait; `ppp tenant` shows the state |

`AUTH`, `SYNTAX` and `BUSY` at the start of an import leave the ZIP unused: the same command can run again. So does `ERROR:` without a kind when pac skips the import because the version online is not lower: pack the version it names (after a restore, `ppp import --restore` again). "As offline" means the card of SKILL.md step 2 or 6; the user's export goes in with `ppp unpack`.

## Restore
`ppp import --restore` brings the newest backup (`exchange/tenant/<Name>/before_<version>.zip`) back, only on the user's decision: `CONFIRM FIRST`, then "Restore" and `--confirmed`. The backup's components get their old content under a higher version; what an import added since stays, a new flow for example [B]. Apps need `--with-apps`. `ppp export` then shows later packages' changes as reverted.
