"""Child process of ppp walk: runs a walk file in the installed Edge with Playwright. Argument: options as JSON."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from ppplib import walk as W
from ppplib.report import Report

QUIET = 2.5  # seconds without a change before a state counts as settled

SCAN = """() => {
  const ids = new Map();
  const id = el => { if (!ids.has(el)) ids.set(el, ids.size); return ids.get(el); };
  const clear = c => !c || c === 'transparent' || /rgba\\(.*,\\s*0\\)$/.test(c);
  const out = [];
  for (const el of document.querySelectorAll('[data-control-name]')) {
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    if (s.visibility === 'hidden' || s.display === 'none' || r.width <= 0 || r.height <= 0) continue;
    const parent = el.parentElement ? el.parentElement.closest('[data-control-name]') : null;
    const p = parent ? parent.getBoundingClientRect() : null;
    let scroller = false;
    for (let a = el.parentElement; a; a = a.parentElement) {
      const o = getComputedStyle(a);
      if (/auto|scroll/.test(o.overflowY + o.overflowX) && (a.scrollHeight > a.clientHeight + 1 || a.scrollWidth > a.clientWidth + 1)) { scroller = true; break; }
    }
    const own = [el, ...el.querySelectorAll('*')].filter(n => n === el || n.closest('[data-control-name]') === el);
    let truncated = false, text = '', broken = false, painted = false;
    for (const n of own) {
      const o = getComputedStyle(n);
      const words = [...n.childNodes].filter(c => c.nodeType === 3).map(c => c.textContent).join('').trim();
      if (words) {
        text = text || words;
        painted = true;
        if (!/auto|scroll/.test(o.overflowY + o.overflowX) && (n.scrollWidth > n.clientWidth + 1 || n.scrollHeight > n.clientHeight + 1)) truncated = true;
      }
      if (n.tagName === 'IMG') { painted = true; if (n.complete && !n.naturalWidth) broken = true; }
      if (n.tagName === 'svg' || n.tagName === 'INPUT' || n.tagName === 'TEXTAREA' || n.tagName === 'SELECT') painted = true;
      if (!clear(o.backgroundColor) || o.backgroundImage !== 'none' || parseFloat(o.borderTopWidth) > 0) painted = true;
    }
    out.push({name: el.getAttribute('data-control-name'), x: r.x, y: r.y, w: r.width, h: r.height, id: id(el),
      parent: parent ? id(parent) : null, parentName: parent ? parent.getAttribute('data-control-name') : '',
      px: p ? p.x : 0, py: p ? p.y : 0, pw: p ? p.width : 0, ph: p ? p.height : 0,
      scroller, transparent: !painted, truncated, broken, text: text.slice(0, 60)});
  }
  return out;
}"""

OVERLAY = """([items, color]) => {
  const root = document.createElement('div');
  root.id = 'ppp-overlay';
  root.style.cssText = 'position:fixed;left:0;top:0;right:0;bottom:0;pointer-events:none;z-index:2147483647';
  for (const i of items) {
    const box = document.createElement('div');
    box.style.cssText = `position:absolute;box-sizing:border-box;left:${i.x}px;top:${i.y}px;width:${i.w}px;height:${i.h}px;`;
    if (i.n) {
      box.style.border = `3px solid ${color}`;
      const tag = document.createElement('div');
      tag.textContent = i.n;
      tag.style.cssText = `position:absolute;left:-3px;top:-3px;transform:translate(-75%,-75%);min-width:22px;height:22px;line-height:22px;border-radius:11px;text-align:center;font:bold 13px Segoe UI,Arial,sans-serif;color:#fff;background:${color}`;
      box.appendChild(tag);
    } else {
      box.style.background = '#8a8a8a';
    }
    root.appendChild(box);
  }
  document.documentElement.appendChild(root);
}"""


class WalkFailed(Exception):
    pass


def boxes(page, name: str) -> list[dict]:
    """Visible boxes of a control across all frames, relative to the window; the runtime may render in a frame."""
    out = []
    for frame in page.frames:
        try:
            loc = frame.locator(f'[data-control-name={json.dumps(name)}]')
            for i in range(loc.count()):
                box = loc.nth(i).bounding_box()
                if box and box["width"] > 0 and box["height"] > 0:
                    out.append(box)
        except PlaywrightError:
            continue  # frame replaced during navigation
    return out


def control_names(page) -> list[str]:
    return sorted({c["name"] for c in scan(page)})


def scan(page) -> list[dict]:
    out = []
    for number, frame in enumerate(page.frames):
        try:
            controls = frame.evaluate(SCAN)
            dx = dy = 0
            if frame != page.main_frame:
                box = frame.frame_element().bounding_box()
                dx, dy = (box["x"], box["y"]) if box else (0, 0)
        except PlaywrightError:
            continue
        for c in controls:
            c["x"] += dx
            c["y"] += dy
            c["px"] += dx
            c["py"] += dy
            c["id"] = f"{number}.{c['id']}"
            c["parent"] = None if c["parent"] is None else f"{number}.{c['parent']}"
        out += controls
    return out


def settle(page, timeout: float) -> None:
    """Wait until the visible controls and their text stop changing."""
    deadline = time.monotonic() + timeout
    last, since = None, time.monotonic()
    while time.monotonic() < deadline:
        state = [(c["name"], round(c["x"]), round(c["y"]), round(c["w"]), round(c["h"]), c["text"]) for c in scan(page)]
        if state != last:
            last, since = state, time.monotonic()
        elif time.monotonic() - since >= QUIET:
            return
        page.wait_for_timeout(250)


def has_content(page, name: str) -> bool:
    script = """el => el.querySelector('[data-control-name]') !== null || (el.innerText || '').trim() !== ''
                      || el.querySelector('img,svg,input') !== null"""
    for frame in page.frames:
        try:
            loc = frame.locator(f'[data-control-name={json.dumps(name)}]')
            for i in range(loc.count()):
                if loc.nth(i).bounding_box() and loc.nth(i).evaluate(script):
                    return True
        except PlaywrightError:
            continue
    return False


def wait_for(page, name: str, timeout: float, refresh: str = "") -> None:
    """Wait for content; on an empty result press refresh and look again. A failed wait stops the walk, so no empty picture."""
    limit = timeout
    for attempt in range(3 if refresh else 1):
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            if has_content(page, name):
                settle(page, timeout)
                return
            page.wait_for_timeout(500)
        limit = timeout / 3
        if refresh and attempt < 2 and boxes(page, refresh):
            click(page, refresh, 0, timeout)
    raise WalkFailed(f"{name} shows no content after {attempt + 1} attempt(s). Controls now: {', '.join(control_names(page)) or 'none'}")


def locate(page, name: str, nth: int, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        found = boxes(page, name)
        if len(found) > nth:
            return found[nth]
        if time.monotonic() >= deadline:
            raise WalkFailed(f"control {name} (nth {nth}) not found; visible: {', '.join(control_names(page)) or 'none'}")
        page.wait_for_timeout(250)


def centre(box: dict) -> tuple[float, float]:
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def click(page, name: str, nth: int, timeout: float) -> None:
    page.mouse.click(*centre(locate(page, name, nth, timeout)))


def take(page, walk: dict, step: dict, folder: Path, mask_seen: set, timeout: float) -> str:
    items = []
    for name in walk.get("mask", []):
        for box in boxes(page, name):
            mask_seen.add(name)
            items.append({"x": box["x"], "y": box["y"], "w": box["width"], "h": box["height"]})
    for number, mark in enumerate(step.get("marks", []), 1):
        name, nth, _ = W.mark_parts(mark)
        box = locate(page, name, nth, timeout)
        items.append({"x": box["x"], "y": box["y"], "w": box["width"], "h": box["height"], "n": number})
    page.evaluate(OVERLAY, [items, walk.get("markColor", "#c00000")])
    target = folder / f"{step['shot']}.png"
    options = {"path": str(target)}
    if step.get("crop"):
        box = locate(page, step["crop"], 0, timeout)
        options["clip"] = {"x": max(box["x"] - 12, 0), "y": max(box["y"] - 12, 0),
                           "width": box["width"] + 24, "height": box["height"] + 24}
    page.screenshot(**options)
    page.evaluate("() => document.getElementById('ppp-overlay').remove()")
    return target.name


def run_steps(page, walk: dict, size: list[int], folder: Path, rep: Report, record: dict, mask_seen: set, timeout: float) -> None:
    ready = walk["ready"]
    wait_for(page, ready["control"], timeout, ready.get("refresh", ""))
    label = f"{size[0]}x{size[1]}"
    for number, step in enumerate(walk["steps"], 1):
        action = W.action_of(step)
        try:
            if action == "wait":
                wait_for(page, step["wait"], timeout)
            elif action == "click":
                click(page, step["click"], step.get("nth", 0), timeout)
            elif action == "hover":
                page.mouse.move(*centre(locate(page, step["hover"], step.get("nth", 0), timeout)))
            elif action == "type":
                click(page, step["type"], step.get("nth", 0), timeout)
                page.keyboard.press("ControlOrMeta+A")
                page.keyboard.type(str(step["value"]))
                page.keyboard.press("Tab")  # OnChange fires when the field loses the focus
            elif action == "key":
                page.keyboard.press(step["key"])
            elif action == "scroll":
                page.mouse.move(*centre(locate(page, step["scroll"], step.get("nth", 0), timeout)))
                page.mouse.wheel(0, step.get("by", 400))
            settle(page, timeout)
            if action == "shot":
                file = take(page, walk, step, folder, mask_seen, timeout)
                controls = scan(page)
                findings = W.layout_findings(controls, size, walk.get("ignore", [])) if step.get("check", True) else []
                for finding in findings:
                    rep.warn(f"{label} {step['shot']}: {finding}")
                record["shots"].append({"viewport": label, "id": step["shot"], "file": str(folder / file),
                                        "findings": findings, "controls": sorted({c["name"] for c in controls})})
        except WalkFailed as ex:
            raise WalkFailed(f"step {number} ({action}): {ex}")


def main(options: dict) -> int:
    path = Path(options["walk"])
    walk = W.load(path)
    folder = Path(options["out"])
    folder.mkdir(parents=True, exist_ok=True)
    timeout = float(options["timeout"])
    rep = Report(f"ppp walk: {W.name_of(path)}")
    record = {"walk": W.name_of(path), "shots": [], "console": [], "http": []}
    mask_seen: set = set()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            options["profile"], channel=options["channel"], headless=options["headless"],
            viewport={"width": W.viewports(walk)[0][0], "height": W.viewports(walk)[0][1]})
        page = context.pages[0] if context.pages else context.new_page()
        page.on("console", lambda m: record["console"].append(m.text[:300]) if m.type == "error" else None)
        page.on("pageerror", lambda e: record["console"].append(str(e)[:300]))

        def note(response):
            if response.status >= 400:
                parts = urlsplit(response.url)  # without the query: it may hold tokens
                record["http"].append(f"{response.status} {parts.netloc}{parts.path}"[:300])
        page.on("response", note)
        page.on("requestfailed", lambda r: record["http"].append(
            f"failed {urlsplit(r.url).netloc}{urlsplit(r.url).path}"[:300]))
        try:
            for number, size in enumerate(W.viewports(walk)):
                if number and W.writes(walk):
                    rep.info(f"{size[0]}x{size[1]} skipped: this walk writes data, it runs once")
                    continue
                target = folder if not number else folder / f"{size[0]}x{size[1]}"
                target.mkdir(parents=True, exist_ok=True)
                page.set_viewport_size({"width": size[0], "height": size[1]})
                page.goto(walk["url"], wait_until="domcontentloaded", timeout=timeout * 1000)
                run_steps(page, walk, size, target, rep, record, mask_seen, timeout)
        except (WalkFailed, PlaywrightError) as ex:
            failed = folder / "failed.png"
            try:
                page.screenshot(path=str(failed))
                rep.info(f"state at the failure: {failed}")
            except PlaywrightError:
                pass
            rep.error(str(ex).splitlines()[0])
        finally:
            context.close()

    if not rep.errors:
        for name in sorted(set(walk.get("mask", [])) - mask_seen):
            rep.error(f"mask {name} was never found; the pictures may show what it should cover")
    for kind, title in (("console", "console errors"), ("http", "failed requests")):
        if record[kind]:
            rep.warn(f"{len(record[kind])} {title}, first: {record[kind][0]}")
    if W.writes(walk) and walk.get("testData"):
        rep.info(f"test data carries the mark {walk['testData'].get('mark')}; remove it: {walk['testData'].get('cleanup')}")
    (folder / "report.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    rep.info(f"{len(record['shots'])} pictures and report.json in {folder}")
    print(rep.text())
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(json.loads(sys.argv[1])))
