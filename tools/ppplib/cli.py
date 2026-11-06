"""Command line `ppp` with subcommands. Exit codes: 0 done, 1 check found errors, 2 tool error."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from . import VERSION, canvas, flows, gitutil, pbi, solution, structure, walk
from .project import ToolError, find_root, load_config, solution_dir
from .report import Report
from .verify import verify

EPILOG = "Exit codes: 0 done, 1 errors found, 2 tool error."


def _split(value: str) -> list[str]:
    return [s.strip() for s in value.split(",") if s.strip()]


def cmd_unpack(a) -> int:
    root = find_root(a.project)
    zip_path = Path(a.zip).resolve()
    if not zip_path.is_file():
        raise ToolError(f"ZIP not found: {zip_path}")
    info = solution.zip_manifest(zip_path)
    target = root / "solution" / info["uniqueName"]
    repo = gitutil.is_repo(root)
    if repo and target.exists() and not a.force:
        dirty = gitutil.git(root, "status", "--porcelain", "--", gitutil.rel(root, target)).decode().strip()
        if dirty:
            raise ToolError(f"Uncommitted changes in {gitutil.rel(root, target)} would be lost. Commit them or use --force.")
    solution.unpack(zip_path, target)
    print(f"Unpacked {zip_path.name} to {gitutil.rel(root, target)}")
    note = structure.register_solution(root, info["uniqueName"])
    if note:
        print(note)
    print("\n".join(solution.summary(target)))
    if not repo:
        print("Not a git repository: nothing committed.")
        return 0
    status = gitutil.git(root, "status", "--porcelain", "--untracked-files=all", "--", gitutil.rel(root, target)).decode()
    changes = [line.strip() for line in status.splitlines() if line.strip()]
    if not changes:
        print("Same content as the last commit.")
        return 0
    added = [c for c in changes if c.startswith("??")]
    if len(added) == len(changes) and not gitutil.tracked_files(root, "HEAD", target, missing_ok=True):
        print(f"New solution folder with {len(added)} files.")
    else:
        print(f"Changed against the last commit ({len(changes)}): M modified, D deleted, ?? added")
        for line in changes[:40]:
            print("  " + line)
        if len(changes) > 40:
            print(f"  … {len(changes) - 40} more")
    if a.no_commit:
        return 0
    message = a.message or f"Export {info['uniqueName']} {info['version']}"
    paths = [gitutil.rel(root, target)] + (["project.json"] if note else [])
    gitutil.git(root, "add", "-A", "--", *paths)
    gitutil.git(root, "commit", "-q", "-m", message, "--", *paths)
    print(f"Committed: {gitutil.describe(root, 'HEAD')}")
    return 0


def cmd_inventory(a) -> int:
    if a.path:
        path = Path(a.path)
        files = [path] if path.is_file() else sorted((path / "Workflows" if (path / "Workflows").is_dir() else path).glob("*.json"))
    else:
        folder = solution_dir(find_root(a.project), a.solution)
        files = sorted((folder / "Workflows").glob("*.json"))
    files = [f for f in files if a.filter.lower() in f.name.lower()]
    if not files:
        raise ToolError("No flow matches.")
    for f in files:
        print("\n".join(flows.inventory(f)))
    return 0


def _base(root: Path, folder: Path, ref: str | None) -> str:
    if ref:
        return gitutil.git(root, "rev-parse", "--verify", ref + "^{commit}").decode().strip()
    return gitutil.base_commit(root, folder)


def cmd_verify(a) -> int:
    root = find_root(a.project)
    folder = solution_dir(root, a.solution)
    base = _base(root, folder, a.base)
    rep = verify(root, folder, base, allowed=_split(a.allowed), retry_none=_split(a.retry_none),
                 check_all=a.all, with_apps=a.with_apps, version_required=False)
    print(f"Base: {gitutil.describe(root, base)}")
    print(rep.text())
    return 1 if rep.errors else 0


def cmd_pack(a) -> int:
    root = find_root(a.project)
    folder = solution_dir(root, a.solution)
    base = _base(root, folder, a.base)
    solution.pac()  # before the version changes
    old = solution.set_version(folder, a.version)
    print(f"Version {old} -> {a.version}")
    rep = verify(root, folder, base, allowed=_split(a.allowed), retry_none=_split(a.retry_none),
                 check_all=a.all, with_apps=a.with_apps)
    info = solution.manifest((folder / "Other" / "Solution.xml").read_bytes())
    stem = f"{info['uniqueName']}_{a.version.replace('.', '_')}" + (f"_{a.label}" if a.label else "")
    out = root / "exchange" / f"{stem}_IMPORTABLE.zip"
    report_path = root / "exchange" / f"{stem}_REPORT.md"
    lines = [f"Base: {gitutil.describe(root, base)}", rep.text()]
    if rep.errors:
        print("\n".join(lines))
        print("Not packed. The version stays set; fix the errors and run ppp pack again.")
        return 1
    solution.pack(folder, out)
    digest = solution.sha256(out)
    lines += ["", f"Package: {out.name}", f"SHA-256: {digest}"]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    print(f"Report: {gitutil.rel(root, report_path)}")
    return 0


TOOLS = Path(__file__).resolve().parent.parent
BLOCKS = TOOLS / "blocks"
PACKAGES = {"yaml": "PyYAML", "docx": "python-docx"}  # module name -> PyPI package, where they differ


def _project_or_none(project: Path | None) -> Path | None:
    try:
        return find_root(project)
    except ToolError:
        return None


def cmd_canvas(a) -> int:
    root = _project_or_none(a.project)
    target = Path(a.path) if a.path else (root / "components" / "power-apps" / "screens" if root else None)
    if not target or not target.exists():
        raise ToolError(f"No screen YAML found at {target}. Give a folder or a .pa.yaml file.")
    files = sorted(target.rglob("*.pa.yaml")) if target.is_dir() else [target]
    if a.versions == "none":
        versions_file = None
    elif a.versions:
        versions_file = Path(a.versions)
    else:
        own = root / "components" / "power-apps" / "generator" / "versionen.py" if root else None
        versions_file = own if own and own.is_file() else BLOCKS / "versionen.py"
    versions = canvas.allowed_versions(versions_file.read_text(encoding="utf-8")) if versions_file else None
    sources = a.sources
    if sources is None and root:
        prefix = load_config(root).get("prefix")
        sources = f"{prefix}_*" if prefix else ""
    rx = canvas.sources_regex(sources or "")
    rep = Report("ppp canvas")
    n_ctl, n_fx = canvas.check(files, versions, rx, rep)
    lines = [f"[{lvl}]".ljust(8) + msg for lvl, msg in rep.lines]
    print("\n".join(lines[:a.max]))
    if len(lines) > a.max:
        print(f"... {len(lines) - a.max} more findings (--max {a.max})")
    print(f"Checked: {len(files)} files, {n_ctl} controls, {n_fx} formulas, {rep.count('INFO')} notes, "
          + (f"version table {versions_file.name} ({len(versions)} entries)" if versions_file else "without version table")
          + (f", sources {sources}" if rx else ", without sources (delegation and refresh not checked)"))
    print(rep.result())
    return 1 if rep.errors else 0


def cmd_pbi(a) -> int:
    root = _project_or_none(a.project)
    target = Path(a.path) if a.path else (root / "components" / "power-bi" if root else None)
    if not target or not target.exists():
        raise ToolError(f"Nothing found at {target}. Give a folder with a PBIP, a .pbip file or a .SemanticModel/.Report folder.")
    base = root or (target.parent if target.is_file() or target.suffix in (".SemanticModel", ".Report") else target)
    models, reports = pbi.load(target)
    if a.action == "list":
        lines = pbi.listing(models, reports, base.resolve())
        print("\n".join(lines[:a.max]))
        if len(lines) > a.max:
            print(f"... {len(lines) - a.max} more lines (--max {a.max})")
        return 0
    rep = Report("ppp pbi check")
    summary = pbi.check(models, reports, rep, base.resolve())
    lines = [f"[{lvl}]".ljust(8) + msg for lvl, msg in rep.lines]
    print("\n".join(lines[:a.max]))
    if len(lines) > a.max:
        print(f"... {len(lines) - a.max} more findings (--max {a.max})")
    print(summary)
    print(rep.result())
    return 1 if rep.errors else 0


def cmd_formulas(a) -> int:
    root = _project_or_none(a.project)
    src = Path(a.file) if a.file else (root / "components" / "power-apps" / "theme" / "App.Formulas.en-US.txt" if root else None)
    if not src or not src.is_file():
        raise ToolError(f"App.Formulas in en-US not found: {src}")
    out = Path(a.out) if a.out else src.with_name(re.sub(r"\.en-US$", "", src.stem) + ".de-DE.txt")
    text = src.read_bytes().decode("utf-8-sig")
    de = canvas.to_de(text)
    out.write_bytes(de.encode("utf-8"))
    problem = canvas.brackets(text)
    print(f"[ERROR] formulas (en-US): {problem}" if problem else "[OK]    formulas (en-US): brackets and strings balanced")
    print(f"[OK]    de-DE written: {out} ({len(de)} characters)")
    return 1 if problem else 0


def cmd_run(a) -> int:
    """Run a project script with the central building blocks importable; the script's own folder comes first."""
    root = find_root(a.project)
    script = (root / a.script).resolve() if not Path(a.script).is_absolute() else Path(a.script)
    if not script.is_file():
        raise ToolError(f"Script not found: {script}")
    return _child(script, a.args, root, BLOCKS)


def _child(script: Path, args: list[str], root: Path, importable: Path) -> int:
    """Run a script in its own Python: unlike python -I it sees packages installed with --user."""
    path = os.pathsep.join(p for p in (str(importable), os.environ.get("PYTHONPATH", "")) if p)
    env = dict(os.environ, PYTHONPATH=path, PPP_PROJEKT=str(root), PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, "-B", str(script), *args], cwd=root, env=env,
                          stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    sys.stderr.write(proc.stderr)
    missing = re.search(r"ModuleNotFoundError: No module named '([A-Za-z0-9_]+)", proc.stderr)
    if proc.returncode and missing:
        name = missing.group(1)
        package = PACKAGES.get(name, name)
        print(f"ppp: the script needs the module {name}. If it is a package from PyPI ({package}), install it after "
              f"the user agreed: \"{sys.executable}\" -m pip install --user {package}. "
              "No virtual environment: group policies often block it.", file=sys.stderr)
    return proc.returncode


def _walk_path(root: Path, given: str) -> Path:
    path = Path(given) if Path(given).is_absolute() else root / given
    if not path.is_file():
        raise ToolError(f"Walk file not found: {path}")
    return path


def cmd_walk(a) -> int:
    root = find_root(a.project)
    path = _walk_path(root, a.file)
    rep = walk.check_file(root, path)
    if a.check or rep.errors:
        print(rep.text())
        return 1 if rep.errors else 0
    loaded = walk.load(path)
    if walk.writes(loaded) and not a.allow_writes:
        print(rep.text())
        print("ERROR: this walk writes data. Confirm on a decision card what it creates, when, what its flows trigger "
              "and how the test data is removed, then run it with --allow-writes.", file=sys.stderr)
        return 1
    for level, message in rep.lines:
        if level == "WARN":
            print(f"[WARN]  {message}")
    profile = Path(a.profile) if a.profile else walk.profile_dir(Path.home(), loaded)
    # response bodies may hold personal data, so they stay outside git whatever the walk's "out" says
    work = root / "exchange" / "walks" / walk.name_of(path)
    diagnosis = work / "diagnosis.json" if a.diagnose else ""
    # a recording keeps apart from the pictures and their baseline
    out = work / "video" if a.video else walk.out_dir(root, path, loaded)
    work = out if a.video else work
    options = {"walk": str(path), "url": walk.resolved_url(root, str(loaded["url"])), "video": a.video, "out": str(out), "profile": str(profile), "diagnosis": str(diagnosis), "work": str(work),
               "screens": walk.screen_hashes(root, loaded),
               "channel": a.channel, "headless": a.headless, "timeout": a.timeout, "signin": a.signin}
    return _child(TOOLS / "child" / "walk_browser.py", [json.dumps(options)], root, TOOLS)


def _bippt(given: str) -> Path | None:
    """The generator bippt of the plugin bi-design: given, else from PPP_BIPPT, the plugins of Claude Code and VS Code, or a
    clone of bi-design beside the ppp repository; the newest one found."""
    if given:
        path = Path(given).expanduser()
        if not path.is_file():
            raise ToolError(f"bippt not found: {path}")
        return path
    if os.environ.get("PPP_BIPPT"):
        return _bippt(os.environ["PPP_BIPPT"])
    home = Path.home()
    roots = [home / ".claude" / "plugins", home / ".vscode", home / ".vscode-insiders",
             home / "Library" / "Application Support" / "Code", Path(os.environ.get("APPDATA", home)) / "Code"]
    found = [p for r in roots if r.is_dir() for p in r.glob("**/bi-design*/**/tools/bippt.py")]
    found += [p for p in [TOOLS.parents[2] / "bi-design" / "plugin" / "tools" / "bippt.py"] if p.is_file()]
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def cmd_guide(a) -> int:
    root = find_root(a.project)
    if a.files[0].endswith(".md"):
        if len(a.files) > 1:
            raise ToolError("A handbook in Markdown comes alone; it names its walks itself with <!-- walk: <name> -->")
        source = Path(a.files[0]) if Path(a.files[0]).is_absolute() else root / a.files[0]
        if not source.is_file():
            raise ToolError(f"Handbook not found: {source}")
        stem = source.stem + ("" if a.kind == "handbook" else f"-{a.kind}")
        if a.role:
            stem += "-" + walk.profile_dir(Path(), {"role": {"name": a.role}}).name.removeprefix("edge-profile-")
        if a.kind == "deck":
            target = Path(a.out) if a.out else Path("docs") / "training" / f"{stem}.pptx"
            options = {"root": str(root), "markdown": str(source), "out": str(root / target), "title": a.title,
                       "role": a.role, "language": load_config(root).get("handbookLanguage", "en"),
                       "bippt": "" if a.bippt == "-" else str(_bippt(a.bippt) or "")}
            return _child(TOOLS / "child" / "walk_deck.py", [json.dumps(options)], root, TOOLS)
        target = Path(a.out) if a.out else source.with_name(f"{stem}.docx")
        options = {"root": str(root), "markdown": str(source), "out": str(root / target), "title": a.title,
                   "template": str(root / a.template) if a.template else "", "role": a.role, "kind": a.kind,
                   "orientation": a.orientation,
                   "language": load_config(root).get("handbookLanguage", "en")}
        code = _child(TOOLS / "child" / "walk_word.py", [json.dumps(options)], root, TOOLS)
        return _word_fields(root / target) if code == 0 and a.word else code
    if a.kind != "handbook":
        raise ToolError("--kind needs a handbook in Markdown with chapters marked <!-- kind: quick|exercises -->; "
                        "a deck is built from the handbook in Markdown")
    paths = [_walk_path(root, name) for name in a.files]
    stem = ""
    if a.role:
        roles = {p: walk.role_name(walk.load(p)) for p in paths}
        paths = [p for p in paths if roles[p] == a.role]
        if not paths:
            raise ToolError(f"No walk for role {a.role}; roles in these walks: {', '.join(sorted(set(filter(None, roles.values())))) or 'none'}")
        stem = "-" + walk.profile_dir(Path(), {"role": {"name": a.role}}).name.removeprefix("edge-profile-")
    target = Path(a.out) if a.out else Path("docs") / "handbook" / f"{walk.name_of(paths[0])}{stem}.docx"
    options = {"root": str(root), "walks": [str(p) for p in paths], "out": str(root / target), "title": a.title,
               "template": str(root / a.template) if a.template else "", "orientation": a.orientation,
               "language": load_config(root).get("handbookLanguage", "en")}
    code = _child(TOOLS / "child" / "walk_word.py", [json.dumps(options)], root, TOOLS)
    return _word_fields(root / target) if code == 0 and a.word else code


WORD_MAC = """on run argv
	set docName to item 1 of argv
	tell application "Microsoft Word"
		set d to document docName
		set pageCount to missing value
		repeat 60 times -- a large document is still loading when it shows up
			try
				set pageCount to compute statistics d statistic statistic pages
				exit repeat
			on error
				delay 2
			end try
		end repeat
		if pageCount is missing value then error docName & " did not finish loading"
		try
			set fieldList to (get fields of d)
		on error
			set fieldList to {} -- a document without fields in its text
		end try
		repeat with f in fieldList
			update field f
		end repeat
		set pageCount to compute statistics d statistic statistic pages
		save d
		close d saving no
		return pageCount
	end tell
end run"""

WORD_WINDOWS = """$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
  $doc = $word.Documents.Open($env:PPP_WORD_FILE)
  foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
  [void]$doc.Fields.Update()
  foreach ($section in $doc.Sections) { foreach ($footer in $section.Footers) { [void]$footer.Range.Fields.Update() } }
  $pages = $doc.ComputeStatistics(2)
  $doc.Save()
  $doc.Close()
  Write-Output $pages
} finally { $word.Quit() }"""


def _word_fields(target: Path) -> int:
    """Open the built file in Microsoft Word, update the table of contents and the other fields, save it: a reader then
    sees page numbers without pressing F9 first. Word picks up fonts installed while it runs only after a restart."""
    import time
    name = target.name
    try:
        if sys.platform == "darwin":
            # opened through Launch Services, Word's sandbox may write the file; an AppleScript open is refused
            subprocess.run(["open", "-a", "Microsoft Word", str(target)], check=True, capture_output=True)
            for _ in range(60):
                names = subprocess.run(["osascript", "-e", 'tell application "Microsoft Word" to get name of documents'],
                                       capture_output=True, text=True).stdout
                if name in names:
                    break
                time.sleep(1)
            else:
                raise ToolError(f"Word did not open {name} within a minute")
            time.sleep(2)  # the document finishes its layout before the fields count pages
            proc = subprocess.run(["osascript", "-", name], input=WORD_MAC, capture_output=True, text=True, timeout=600)
        elif sys.platform == "win32":
            # powershell -Command passes no further arguments to $args, so Word got no file: the path goes by environment
            proc = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", WORD_WINDOWS],
                                  env={**os.environ, "PPP_WORD_FILE": str(target)}, capture_output=True, text=True, timeout=600)
        else:
            raise ToolError("--word needs Microsoft Word on macOS or Windows")
    except (OSError, subprocess.SubprocessError) as ex:
        raise ToolError(f"Word could not update {name}: {ex}")
    if proc.returncode:
        raise ToolError(f"Word could not update {name}: {(proc.stderr or proc.stdout).strip()}")
    print(f"{name}: fields updated in Word, {proc.stdout.strip()} pages")
    return 0


def cmd_init(a) -> int:
    root = Path(a.folder).resolve() if a.folder else Path.cwd()
    modules = _split(a.modules)
    lines = structure.init(root, a.name, a.prefix, modules, a.mode, a.language, a.solution or None)
    print("\n".join(lines))
    rep = structure.check(root)
    print(rep.text())
    return 1 if rep.errors else 0


def cmd_setup(a) -> int:
    from . import agent
    print("\n".join(agent.setup()))
    return 0


def cmd_settings(a) -> int:
    from . import agent
    if not a.language and not a.guidance and not a.sessions:
        current = agent.read_settings()
        print(f"{agent.SETTINGS}: {current}" if current else f"{agent.SETTINGS} is missing. "
              "Set it with --language <code> --guidance beginner|standard|experienced.")
        return 0
    print(f"Saved {agent.SETTINGS}: {agent.write_settings(a.language, a.guidance, a.sessions)}")
    return 0


def cmd_check(a) -> int:
    from . import agent
    root = find_root(a.project)
    update = agent.update_clone()
    rep = structure.check(root, update, agent.agent_note())
    print(rep.text())
    return 1 if rep.errors else 0


def cmd_migrate(a) -> int:
    print("\n".join(structure.migrate(find_root(a.project))))
    return 0


def cmd_new(a) -> int:
    root = find_root(a.project)
    if a.kind == "spec-delta":
        package, _, capability = a.title.partition(":")
        path = structure.spec_delta(root, package.strip(), capability.strip())
    else:
        path = structure.new(root, a.kind, a.title, "WIN" if sys.platform == "win32" else "MAC")
    print(f"Created {gitutil.rel(root, path)}")
    return 0


def cmd_archive(a) -> int:
    print("\n".join(structure.archive(find_root(a.project), a.package)))
    return 0


def cmd_tidy(a) -> int:
    from . import exchange
    root = find_root(a.project)
    print("\n".join(structure.remove_leftovers(root, a.dry_run) if a.leftovers else exchange.tidy(root, a.keep, a.dry_run)))
    return 0


def cmd_mail(a) -> int:
    from . import mail
    print("\n".join(mail.show(Path(a.file), Path(a.out) if a.out else None)))
    return 0


def _schema_path(root: Path, given: str) -> Path:
    path = Path(given) if given else root / "components" / "sharepoint" / "schema.json"
    if not path.is_file():
        raise ToolError(f"schema.json not found: {path}")
    return path


def cmd_schema(a) -> int:
    from . import schema
    root = _project_or_none(a.project)
    path = Path(a.path) if a.path else (root / "components" / "sharepoint" / "schema.json" if root else Path("schema.json"))
    if not path.is_file():
        raise ToolError(f"schema.json not found: {path}")
    rep = Report(f"ppp schema | {path.name}")
    schema.check(schema.load(path), load_config(root).get("prefix") if root else None, rep)
    print(rep.text())
    return 1 if rep.errors else 0


def cmd_setupflow(a) -> int:
    import json

    from . import flows as fl
    from . import schema, setupflow
    from .verify import MAX_DEPTH
    root = find_root(a.project)
    prefix = load_config(root).get("prefix")
    if not prefix:
        raise ToolError("project.json has no prefix")
    path = _schema_path(root, a.schema)
    definition = schema.load(path)
    rep = Report("schema.json")
    schema.check(definition, prefix, rep)
    if rep.errors:
        print(rep.text())
        raise ToolError("schema.json has errors; the setup flow was not built")
    folder = solution_dir(root, a.solution)
    wanted = a.flow or f"{prefix}_Setup"
    candidates = [f for f in sorted((folder / "Workflows").glob("*.json"))
                  if re.sub(r"-[0-9A-Fa-f-]{36}$", "", f.stem) == wanted or (a.flow and a.flow.lower() in f.name.lower())]
    if len(candidates) != 1:
        raise ToolError(f"Expected one flow {wanted} in {gitutil.rel(root, folder)}/Workflows, found {len(candidates)}. "
                        "Create the scaffold in the designer (manual trigger with text input Phase, one Send an HTTP request "
                        "to SharePoint, Respond to a PowerApp or flow with output ergebnis), export and unpack it.")
    flow_file = candidates[0]
    raw = flow_file.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ToolError(f"{flow_file.name} starts with a BOM; exported flows have none")
    text = raw.decode("utf-8")
    workflow = json.loads(text)
    try:
        http_t, response_t, phase_key, note = setupflow.templates(workflow)
    except setupflow.ScaffoldError as ex:
        raise ToolError(f"{flow_file.name}: {ex}") from ex
    actions, writing = setupflow.build(definition, prefix, http_t, response_t, phase_key)
    new_text = setupflow.replace_value(text, "actions", actions, after_marker='"definition":')
    if json.loads(new_text)["properties"]["definition"]["actions"] != actions:
        raise ToolError("internal: actions not replaced as built")
    every = list(fl.walk(actions))
    depth = max(lvl for *_, lvl in every)
    if depth > MAX_DEPTH:
        raise ToolError(f"nesting depth {depth} > {MAX_DEPTH}")
    flow_file.write_bytes(new_text.encode("utf-8"))
    print(f"Setup flow written: {gitutil.rel(root, flow_file)}")
    print(f"  {len(every)} actions, nesting depth {depth}/{MAX_DEPTH}, schema {definition.get('schemaVersion', definition.get('version'))}, "
          f"{len(definition['listen'])} lists, setup parts: {', '.join(sorted(definition.get('setup') or {})) or 'none'}")
    if note:
        print(f"  Note: {note}")
    print(f"  Writing actions ({len(writing)}) have retryPolicy none. Check: ppp verify --retry-none {','.join(writing)}")
    return 0


def cmd_usage(a) -> int:
    from datetime import date, datetime, timezone

    from . import usage
    if a.since:
        since = datetime.fromisoformat(a.since).replace(tzinfo=timezone.utc)
    else:
        start = usage.period_start(date.today())
        since = datetime(start.year, start.month, start.day).astimezone()
    sessions = usage.collect(Path(a.home).expanduser() if a.home else Path.home(), since, a.filter)
    if a.json:
        import json
        print(json.dumps(usage.as_json(sessions), ensure_ascii=False, indent=1))
    else:
        print("\n".join(usage.table(sessions, since)))
    return 0


def cmd_sessions(a) -> int:
    from datetime import datetime

    from . import agent, sessions
    repo = a.repo or (agent.read_settings() or {}).get("sessionsRepo")
    if not repo:
        raise ToolError("No sessions repository set. Save the folder of its clone with ppp settings --sessions <folder>.")
    since = datetime.fromisoformat(a.since).timestamp() if a.since else None
    home = Path(a.home).expanduser() if a.home else Path.home()
    print("\n".join(sessions.upload(Path(repo).expanduser(), home, since, a.dry_run)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ppp", description="ppp tools for Power Platform solutions.", epilog=EPILOG)
    p.add_argument("--version", action="version", version=f"ppp {VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    def command(name: str, func, help_text: str, solution_arg: bool = True) -> argparse.ArgumentParser:
        c = sub.add_parser(name, help=help_text, description=help_text, epilog=EPILOG)
        c.add_argument("--project", type=Path, default=None, help="project folder (default: nearest with project.json)")
        if solution_arg:
            c.add_argument("--solution", default=None,
                           help="unique name of the solution (default: the transfer solution, else the main solution)")
        c.set_defaults(func=func)
        return c

    c = command("unpack", cmd_unpack, "Unpack an export ZIP with pac to solution/<UniqueName>/ and commit it as 'Export <name> <version>'.", False)
    c.add_argument("zip", help="export ZIP, usually in exchange/")
    c.add_argument("--no-commit", action="store_true", help="unpack only")
    c.add_argument("--message", default="", help="commit message instead of 'Export <name> <version>'")
    c.add_argument("--force", action="store_true", help="replace the folder even with uncommitted changes")

    c = command("inventory", cmd_inventory, "List flows compactly: trigger, connection references, action tree with type, line and runAfter.")
    c.add_argument("filter", nargs="?", default="", help="part of the flow file name")
    c.add_argument("--path", default="", help="a workflow JSON or a folder instead of the project solution")

    def check_args(c):
        c.add_argument("--base", default=None, help="git ref to compare with (default: commit of the current solution version)")
        c.add_argument("--allowed", default="", help="comma-separated files that may change, as C4 names them or by a file name that matches one changed file (Other/Solution.xml always)")
        c.add_argument("--retry-none", default="", help="comma-separated actions that need retryPolicy none")
        c.add_argument("--all", action="store_true", help="check every flow, not only changed ones")
        c.add_argument("--with-apps", action="store_true", help="apps stay in the package (move to test or production only)")

    c = command("verify", cmd_verify, "Check the solution folder against the base (C1-C14) without packing; "
                                      "a version not raised yet (C5) is only a hint, ppp pack raises it.")
    check_args(c)

    c = command("pack", cmd_pack, "Set the version, check (C1-C14) and pack the solution (default: the transfer solution, else "
                                  "the main solution) with pac to exchange/ with a report.")
    c.add_argument("--version", required=True, dest="version", help="new four-part version, e.g. 1.0.0.23")
    c.add_argument("--label", default="", help="short label in the file name")
    check_args(c)

    c = command("canvas", cmd_canvas, "Check screen YAML before pasting: formulas, en-US, control versions, containers, delegation.", False)
    c.add_argument("path", nargs="?", default="", help="folder or .pa.yaml (default: components/power-apps/screens)")
    c.add_argument("--versions", default="", help="file with Type@Version entries (default: the project's generator/versionen.py, "
                                                  "else the central one); 'none' skips the check")
    c.add_argument("--sources", default=None, help="data source patterns such as 'ASUM_*' (default: <prefix>_* from project.json)")
    c.add_argument("--max", type=int, default=60, help="findings shown (default 60)")

    c = command("pbi", cmd_pbi, "Power BI as PBIP: list the model (TMDL or model.bim) and the report pages compactly, or check "
                                "them before opening in Desktop (field references, names, BOM, $schema, time functions, "
                                ".pbi data files in git). Reads PBIP only, no PBIX and no row data.", False)
    c.add_argument("action", choices=("list", "check"), help="list: one line per object; check: findings, exit code 1 on errors")
    c.add_argument("path", nargs="?", default="", help="folder, .pbip file or one .SemanticModel/.Report folder "
                                                       "(default: components/power-bi)")
    c.add_argument("--max", type=int, default=400, help="lines shown (default 400)")

    c = command("formulas", cmd_formulas, "Convert App.Formulas from en-US to de-DE and check brackets.", False)
    c.add_argument("file", nargs="?", default="", help="App.Formulas in en-US (default: components/power-apps/theme/App.Formulas.en-US.txt)")
    c.add_argument("--out", default="", help="target file (default: same name with .de-DE.txt)")

    c = command("mail", cmd_mail, "Show an Outlook message (.msg) without Outlook: subject, sender, recipients, date, body "
                                  "(text, else HTML as text) and attachments.", False)
    c.add_argument("file", help=".msg file, e.g. in exchange/ or inputs/")
    c.add_argument("--out", default="", help="folder for the attachments (equal names are numbered)")

    c = command("run", cmd_run,"Run a project generator or test with the central building blocks (bausteine, pfx, versionen, wdl_sim).", False)
    c.add_argument("script", help="script path relative to the project")
    c.add_argument("args", nargs=argparse.REMAINDER, help="arguments for the script")

    c = sub.add_parser("init", help="Create the core of a ppp project in a folder; existing files stay untouched.",
                       description="Create the core of a ppp project (README, AGENTS, CLAUDE, STATE, ROADMAP, project.json, "
                                   "core folders, components/<module>/README.md); existing files stay untouched.", epilog=EPILOG)
    c.add_argument("folder", nargs="?", default="", help="project folder (default: current folder)")
    c.add_argument("--name", required=True, help="project name, e.g. 'ASUM – Automatic SharePoint User Management'")
    c.add_argument("--prefix", required=True, help="prefix before flows, lists and components, e.g. ASUM")
    c.add_argument("--modules", default="", help="comma-separated: " + ", ".join(structure.MODULES))
    c.add_argument("--mode", default="medium", choices=structure.MODES)
    c.add_argument("--language", default="de", help="language of handbook and training (default de)")
    c.add_argument("--solution", default="", help="unique name of the main solution, if it exists already")
    c.set_defaults(func=cmd_init)

    command("check", cmd_check, "Report deviations from the project structure (target: none) and an old agent copy "
                                "that hides the agent of the plugin; updates the ppp clone (git pull --ff-only) when it "
                                "is behind its upstream and clean; creates a missing exchange/.", False)

    c = sub.add_parser("setup", help="Remove an old agent copy (~/.copilot/agents/ppp.agent.md) and show the installation entries.",
                       description="Remove the agent copy of ppp before 0.2.0 (~/.copilot/agents/ppp.agent.md), which hides "
                                   "the agent of the plugin, keep the tool call in ~/.ppp/tool-call.txt and show the "
                                   "installation entries for VS Code and Claude Code.", epilog=EPILOG)
    c.set_defaults(func=cmd_setup)
    c = sub.add_parser("settings", help="Show or save the personal settings (~/.ppp/settings.json).",
                       description="Show or save the personal settings in ~/.ppp/settings.json: language of chat and cards, "
                                   "guidance level, folder of the sessions repository.", epilog=EPILOG)
    c.add_argument("--language", default="", help="language of chat and cards, e.g. de or en")
    c.add_argument("--guidance", default="", help="beginner, standard or experienced")
    c.add_argument("--sessions", default="", help="folder of the clone of the private sessions repository (ppp sessions)")
    c.set_defaults(func=cmd_settings)
    command("migrate", cmd_migrate, "Bring the project to the current structure version.", False)

    c = command("new", cmd_new, "Create a file from a template with the next free number.", False)
    c.add_argument("kind", choices=("package", "design", "decision", "spec", "spec-delta", "lesson"),
                   help="package: changes/NNN-name/ with proposal.md and tasks.md · design: design.md in a package "
                        "(title = package number) · decision: decisions/NNN-name.md · spec: specs/<name>.md · "
                        "spec-delta: '<package number>: <capability>' · lesson: '<area>: <title>' in lessons/ with area "
                        "one of " + ", ".join(structure.AREAS))
    c.add_argument("title", help="title or name")

    c = command("schema", cmd_schema, "Check components/sharepoint/schema.json (lists, fields, start values, setup parts).", False)
    c.add_argument("path", nargs="?", default="", help="schema.json (default: components/sharepoint/schema.json)")

    c = command("setupflow", cmd_setupflow, "Write the setup flow logic from schema.json into the exported scaffold <prefix>_Setup.")
    c.add_argument("--flow", default="", help="part of the flow file name, if it is not <prefix>_Setup")
    c.add_argument("--schema", default="", help="schema.json (default: components/sharepoint/schema.json)")

    c = command("archive", cmd_archive, "Move a finished package to changes/archive/ (all tasks must be checked).", False)
    c.add_argument("package", help="package number (e.g. 003) or folder name")

    c = command("tidy", cmd_tidy, "Tidy exchange/ after a package: the imported package with its report to exchange/archive/, "
                                  "the other packages and the older exports of each solution deleted, other files listed.", False)
    c.add_argument("--keep", nargs="+", default=None, metavar="ZIP",
                   help="packages to archive (default: the newest of the transfer solution, else of the main solution)")
    c.add_argument("--leftovers", action="store_true",
                   help="instead: remove local leftover folders outside git and the structure that hold no files "
                        "(read-only ones too, links never followed); folders with files are only listed")
    c.add_argument("--dry-run", action="store_true", help="show the plan only")

    c = sub.add_parser("usage", help="Usage per session from the session logs of Copilot and Claude Code (for evaluation).",
                       description="Usage per session from the session logs of Copilot and Claude Code: AIU, tokens, models, "
                                   "subagents. For evaluation from outside; it has no target value.", epilog=EPILOG)
    c.add_argument("--since", default="", help="YYYY-MM-DD (default: start of the current budget quarter: day 1, 9, 17 or 25)")
    c.add_argument("--filter", default="", help="part of the project folder name")
    c.add_argument("--json", action="store_true", help="one record per session as JSON")
    c.add_argument("--home", default="", help="home folder with .copilot and .claude (default: the user's)")
    c.set_defaults(func=cmd_usage)

    c = sub.add_parser("sessions", help="Upload the session logs of ppp projects that changed since the last upload to the "
                                        "sessions repository (for a learning session).",
                       description="Copy the Copilot session logs of ppp projects (working folder with project.json) that "
                                   "changed since the last upload of this computer into the clone of the sessions "
                                   "repository (sessionsRepo in ~/.ppp/settings.json), commit and push.", epilog=EPILOG)
    c.add_argument("--repo", default="", help="folder of the clone (default: sessionsRepo from the settings)")
    c.add_argument("--since", default="", help="YYYY-MM-DD: take sessions changed on or after this day (default: the last upload)")
    c.add_argument("--dry-run", action="store_true", help="only list the sessions, copy and push nothing")
    c.add_argument("--home", default="", help="home folder with .copilot (default: the user's)")
    c.set_defaults(func=cmd_sessions)

    c = command("walk", cmd_walk, "Run a walk file through the running app in Edge: clicks, pictures, measured layout findings, console and HTTP errors. Needs the package playwright.", False)
    c.add_argument("file", help="walk file (JSON), usually in docs/handbook/walks/ or tests/walks/")
    c.add_argument("--check", action="store_true", help="only check the walk file offline, no browser")
    c.add_argument("--allow-writes", action="store_true", help="run steps marked writes, after the user confirmed them on a card")
    c.add_argument("--diagnose", action="store_true", help="record every error of the app per step, with the bodies of failed responses, in exchange/walks/<name>/diagnosis.json")
    c.add_argument("--video", action="store_true", help="record the walk with captions and a click ring to exchange/walks/<name>/video/<name>.webm instead of taking pictures; needs ffmpeg from playwright")
    c.add_argument("--channel", default="msedge", help="installed browser (default: msedge)")
    c.add_argument("--headless", action="store_true", help="without a window; company sign-in usually needs the window")
    c.add_argument("--profile", default="", help="browser profile folder (default: ~/.ppp/edge-profile, per role ~/.ppp/edge-profile-<role>)")
    c.add_argument("--timeout", type=float, default=90, help="seconds to wait for the app at the start and for content or a control at each step (default: 90)")
    c.add_argument("--signin", type=float, default=600, help="seconds to wait while a sign-in page is open, for the user to sign in (default: 600)")

    c = command("guide", cmd_guide, "Build a Word guide from a handbook in Markdown that names its walks with <!-- walk: <name> -->, or from walk files, one chapter per walk; with the walks' pictures. From one handbook: the whole handbook, the handbook of a role (sections marked <!-- for: <roles> -->), a quick guide or an exercise sheet (chapters marked <!-- kind: quick|exercises -->), or the training deck of a role in PowerPoint (--kind deck). Needs the package python-docx.", False)
    c.add_argument("files", nargs="+", help="the handbook docs/handbook/<name>.md, or walk files in chapter order")
    c.add_argument("--out", default="", help="Word file (default: docs/handbook/<name>[-<kind>][-<role>].docx, for walks <first walk>.docx); deck: docs/training/<name>-deck[-<role>].pptx, its spec beside it")
    c.add_argument("--title", default="", help="document title (default: the handbook's # title, with ' – <role>' for a role)")
    c.add_argument("--role", default="", help="handbook: only the sections for this role; walks: only the walks of this role")
    c.add_argument("--kind", default="handbook", choices=("handbook", "quick", "exercises", "deck"), help="handbook (default), quick guide or exercise sheet, from the chapters of that kind; deck: a compact training deck of the role in the corporate design (handbook chapters with one slide per task, quick guide, exercises with hidden solutions), built with bippt of the plugin bi-design")
    c.add_argument("--bippt", default="", help="deck: path to bippt.py of the plugin bi-design (default: found from PPP_BIPPT or the installed plugins); - writes the spec only")
    c.add_argument("--orientation", default="", choices=("", "portrait", "landscape"), help="page orientation of every section (default: as the template has it)")
    c.add_argument("--word", action="store_true", help="then open the file in Microsoft Word (macOS or Windows), update table of contents and fields, save it and print its pages")
    c.add_argument("--template", default="", help="Word template to fill, its styles apply")

    # one call of ppp --help shows every command with its options
    usages = "\n".join(c.format_usage().replace("usage: ", "  ", 1).rstrip() for c in sub.choices.values())
    p.epilog = f"Commands with their options (details: ppp <command> --help):\n{usages}\n\n{EPILOG}"
    p.formatter_class = argparse.RawDescriptionHelpFormatter
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ToolError, OSError) as ex:  # file errors too, as one line instead of a traceback
        print(f"ERROR: {ex}", file=sys.stderr)
        return 2
