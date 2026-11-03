"""Child process of ppp walk: runs a walk file in the installed Edge with Playwright. Argument: options as JSON."""
from __future__ import annotations

import base64
import json
import shutil
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
  const rgb = c => { const m = /rgba?\\(([^)]+)\\)/.exec(c || ''); return m ? m[1].split(',').map(Number) : null; };
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
    let truncated = false, split = '', text = '', broken = false, painted = false, interactive = false, labelled = false, fg = null, bg = null;
    for (const n of own) {
      const o = getComputedStyle(n);
      const words = [...n.childNodes].filter(c => c.nodeType === 3).map(c => c.textContent).join('').trim();
      if (words) {
        text = text || words;
        painted = true;
        if (!fg) {
          fg = rgb(o.color);
          for (let a = n; a && !bg; a = a.parentElement) {
            const c = rgb(getComputedStyle(a).backgroundColor);
            if (getComputedStyle(a).backgroundImage !== 'none') break;  // on a picture no colour can be judged
            if (c && (c.length < 4 || c[3] === 1)) bg = c;
          }
        }
        if (!/auto|scroll/.test(o.overflowY + o.overflowX) && (n.scrollWidth > n.clientWidth + 1 || n.scrollHeight > n.clientHeight + 1)) truncated = true;
        for (const t of [...n.childNodes].filter(c => c.nodeType === 3 && c.textContent.trim())) {
          const range = document.createRange(); range.selectNodeContents(t);
          const parts = [...range.getClientRects()].filter(q => q.width > 0);
          // text cut by a clipping box inside the control, e.g. beside the chevron of a dropdown; the rectangles hold
          // ascent and descent, so a small overhang is font metrics (PAPPS-20261103-WIN-02, PAPPS-20261103-WIN-03)
          for (let a = n; a && !truncated; a = a === el ? null : a.parentElement) {
            const ao = getComputedStyle(a), q = a.getBoundingClientRect();
            if (/auto|scroll/.test(ao.overflowY + ao.overflowX) && (a.scrollHeight > a.clientHeight + 1 || a.scrollWidth > a.clientWidth + 1)) continue;
            const x = /hidden|clip|auto|scroll/.test(ao.overflowX), y = /hidden|clip|auto|scroll/.test(ao.overflowY);
            truncated = parts.some(r => (x && (r.left < q.left - 1 || r.right > q.right + 1)) || (y && (r.top < q.top - 2 || r.bottom > q.bottom + 2)));
          }
          for (const m of t.textContent.matchAll(/\\S{2,}/g)) {
            range.setStart(t, m.index); range.setEnd(t, m.index + m[0].length);
            const tops = [...range.getClientRects()].filter(q => q.width > 0).map(q => q.top).sort((a, b) => a - b);
            if (!split && tops.some((top, i) => i > 0 && top - tops[i - 1] > 2)) split = m[0];
          }
        }
      }
      if (n.tagName === 'BUTTON' || n.tagName === 'A' || n.getAttribute('role') === 'button') interactive = true;
      if (n.getAttribute('aria-label') || n.getAttribute('title') || n.getAttribute('alt')) labelled = true;
      if (n.tagName === 'IMG') { painted = true; if (n.complete && !n.naturalWidth) broken = true; }
      if (n.tagName === 'svg' || n.tagName === 'INPUT' || n.tagName === 'TEXTAREA' || n.tagName === 'SELECT') painted = true;
      if (!clear(o.backgroundColor) || o.backgroundImage !== 'none' || parseFloat(o.borderTopWidth) > 0) painted = true;
    }
    let lines = 0, cut = '';
    const label = interactive && own.find(n => [...n.childNodes].some(c => c.nodeType === 3 && c.textContent.trim()));
    if (label) {
      const range = document.createRange(); range.selectNodeContents(label);
      const tops = [...range.getClientRects()].filter(q => q.width > 0).map(q => q.top).sort((a, b) => a - b);
      lines = tops.filter((t, i) => i === 0 || t - tops[i - 1] > 2).length;
    }
    // a classic button paints its border on a layer with margin -0.5px, outside its own box (PAPPS-20261103-WIN-01)
    const layer = own.find(n => n.classList && n.classList.contains('appmagic-borderfill-container')) || el;
    const ls = getComputedStyle(layer), b = layer.getBoundingClientRect();
    if (['Top', 'Right', 'Bottom', 'Left'].some(k => parseFloat(ls['border' + k + 'Width']) > 0)) {
      for (let a = layer.parentElement; a && !cut; a = a.parentElement) {
        const o = getComputedStyle(a), q = a.getBoundingClientRect();
        if (/auto|scroll/.test(o.overflowY + o.overflowX) && (a.scrollHeight > a.clientHeight + 1 || a.scrollWidth > a.clientWidth + 1)) continue;
        if (q.right <= b.left || q.left >= b.right || q.bottom <= b.top || q.top >= b.bottom) continue;
        const x = /hidden|clip|auto|scroll/.test(o.overflowX), y = /hidden|clip|auto|scroll/.test(o.overflowY);
        const lost = [y ? q.top - b.top : 0, x ? b.right - q.right : 0, y ? b.bottom - q.bottom : 0, x ? q.left - b.left : 0];
        const sides = ['top', 'right', 'bottom', 'left'].filter((_, i) => lost[i] > 0.1);
        const owner = a.closest('[data-control-name]');
        if (sides.length) cut = `${owner ? owner.getAttribute('data-control-name') : a.tagName.toLowerCase()} (${sides.join(', ')})`;
      }
    }
    out.push({name: el.getAttribute('data-control-name'), x: r.x, y: r.y, w: r.width, h: r.height, id: id(el),
      parent: parent ? id(parent) : null, parentName: parent ? parent.getAttribute('data-control-name') : '',
      px: p ? p.x : 0, py: p ? p.y : 0, pw: p ? p.width : 0, ph: p ? p.height : 0,
      scroller, transparent: !painted, truncated, broken, text: text.slice(0, 60), interactive, labelled: labelled || !!text, fg, bg,
      lines, cut, split});
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

# the part of a control its clipping parents leave visible, in its frame; a frame around the whole box landed on other
# content (PAPPS-20261103-WIN-06)
EXPOSED = """el => {
  const r = el.getBoundingClientRect();
  let left = Math.max(0, r.left), top = Math.max(0, r.top), right = Math.min(innerWidth, r.right), bottom = Math.min(innerHeight, r.bottom);
  for (let a = el.parentElement; a; a = a.parentElement) {
    const s = getComputedStyle(a), b = a.getBoundingClientRect(), x = b.left + a.clientLeft, y = b.top + a.clientTop;
    if (s.display === 'none' || s.visibility === 'hidden') return {x: r.x, y: r.y, width: 0, height: 0, ratio: 0, fullX: r.x, fullY: r.y};
    if (/hidden|clip|auto|scroll/.test(s.overflowX)) { left = Math.max(left, x); right = Math.min(right, x + a.clientWidth); }
    if (/hidden|clip|auto|scroll/.test(s.overflowY)) { top = Math.max(top, y); bottom = Math.min(bottom, y + a.clientHeight); }
  }
  const width = Math.max(0, right - left), height = Math.max(0, bottom - top);
  return {x: left, y: top, width, height, ratio: width * height / Math.max(1, r.width * r.height), fullX: r.x, fullY: r.y};
}"""

# a marked control into view inside the app's scrolling containers, as little as needed; the page itself stays
SCROLL_INTO_VIEW = """el => {
  for (let a = el.parentElement; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
    const s = getComputedStyle(a), b = a.getBoundingClientRect();
    for (const [over, start, end, pos, size, edge] of [['overflowY', 'top', 'bottom', 'scrollTop', 'clientHeight', 'clientTop'],
                                                        ['overflowX', 'left', 'right', 'scrollLeft', 'clientWidth', 'clientLeft']]) {
      if (!/auto|scroll/.test(s[over])) continue;
      const r = el.getBoundingClientRect(), low = b[start] + a[edge], high = low + a[size];
      if (r[start] < low) a[pos] -= low - r[start];
      else if (r[end] > high) a[pos] += Math.min(r[end] - high, r[start] - low);
    }
  }
}"""

# a selection painted blue over the page in a guide picture (PAPPS-20261103-WIN-06)
CLEAR_SELECTION = """() => {
  getSelection()?.removeAllRanges();
  const f = document.activeElement;
  if (f && /^(INPUT|TEXTAREA)$/.test(f.tagName)) {
    try { f.setSelectionRange(f.value.length, f.value.length); } catch (e) {}
    f.blur();
  }
}"""


COMPARE = """async ([before, after]) => {
  const load = src => new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = 'data:image/png;base64,' + src; });
  const [a, b] = [await load(before), await load(after)];
  if (a.width !== b.width || a.height !== b.height) return {size: `${a.width}x${a.height} -> ${b.width}x${b.height}`};
  const canvas = n => { const c = document.createElement('canvas'); c.width = n.width; c.height = n.height; const g = c.getContext('2d'); g.drawImage(n, 0, 0); return [c, g]; };
  const [, ga] = canvas(a), [cb, gb] = canvas(b);
  const da = ga.getImageData(0, 0, a.width, a.height), db = gb.getImageData(0, 0, b.width, b.height);
  let changed = 0, left = a.width, top = a.height, right = -1, bottom = -1;
  for (let y = 0, i = 0; y < a.height; y++) for (let x = 0; x < a.width; x++, i += 4) {
    const differs = Math.max(Math.abs(da.data[i] - db.data[i]), Math.abs(da.data[i+1] - db.data[i+1]), Math.abs(da.data[i+2] - db.data[i+2])) > 16;
    if (differs) {
      changed++; left = Math.min(left, x); top = Math.min(top, y); right = Math.max(right, x); bottom = Math.max(bottom, y);
      db.data[i] = 255; db.data[i+1] = 0; db.data[i+2] = 0;
    } else for (let k = 0; k < 3; k++) db.data[i+k] = 255 - (255 - db.data[i+k]) / 3;
  }
  if (!changed) return {percent: 0};
  gb.putImageData(db, 0, 0);
  return {percent: 100 * changed / (a.width * a.height), box: [left, top, right - left + 1, bottom - top + 1], diff: cb.toDataURL('image/png').split(',')[1]};
}"""

# up to six pictures side by side with their names: one image to look at instead of six, so a guide's pictures do not
# fill the chat
SHEET = """async ([pictures, names]) => {
  const load = src => new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = 'data:image/png;base64,' + src; });
  const images = await Promise.all(pictures.map(load));
  const COLS = 2, WIDTH = 760, GAP = 16, LABEL = 26;
  const sizes = images.map(i => { const w = Math.min(WIDTH, i.width); return [w, Math.round(i.height * w / i.width)]; });
  const rows = [];
  for (let r = 0; r * COLS < images.length; r++) rows.push(Math.max(...sizes.slice(r * COLS, r * COLS + COLS).map(s => s[1])) + LABEL + GAP);
  const c = document.createElement('canvas');
  c.width = COLS * WIDTH + (COLS + 1) * GAP; c.height = rows.reduce((a, b) => a + b, GAP);
  const g = c.getContext('2d');
  g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
  g.font = 'bold 16px Segoe UI, Arial, sans-serif'; g.strokeStyle = '#888';
  let y = GAP;
  rows.forEach((height, r) => {
    for (let k = 0; k < COLS && r * COLS + k < images.length; k++) {
      const n = r * COLS + k, x = GAP + k * (WIDTH + GAP), [w, h] = sizes[n];
      g.fillStyle = '#000'; g.fillText(names[n], x, y + 18);
      g.drawImage(images[n], x, y + LABEL, w, h); g.strokeRect(x, y + LABEL, w, h);
    }
    y += height;
  });
  return c.toDataURL('image/png').split(',')[1];
}"""


POINTER = """([x, y, color]) => {
  const dot = document.createElement('div');
  dot.className = 'ppp-pointer';
  dot.style.cssText = `position:fixed;left:${x - 18}px;top:${y - 18}px;width:36px;height:36px;border-radius:18px;border:4px solid ${color};box-sizing:border-box;pointer-events:none;z-index:2147483647`;
  document.documentElement.appendChild(dot);
  setTimeout(() => dot.remove(), 900);
}"""

CAPTION = """text => {
  let bar = document.getElementById('ppp-caption');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'ppp-caption';
    bar.style.cssText = 'position:fixed;left:0;right:0;bottom:0;padding:12px 24px;font:18px Segoe UI,Arial,sans-serif;color:#fff;background:rgba(0,0,0,.78);pointer-events:none;z-index:2147483647';
    document.documentElement.appendChild(bar);
  }
  bar.textContent = text;
}"""


def mask_script(names: list[str]) -> str:
    """For a video: masks as a style in every frame from its first moment, so no frame of the recording shows them."""
    rules = "".join(f'[data-control-name={json.dumps(n)}]{{background:#8a8a8a!important;color:transparent!important}}'
                    f'[data-control-name={json.dumps(n)}] *,img[data-control-name={json.dumps(n)}]{{visibility:hidden!important}}'
                    for n in names)
    return f"""(() => {{
      const add = () => {{ const s = document.createElement('style'); s.textContent = {json.dumps(rules)}; document.documentElement.appendChild(s); }};
      if (document.documentElement) add();
      else new MutationObserver((_, o) => {{ if (document.documentElement) {{ o.disconnect(); add(); }} }}).observe(document, {{childList: true}});
    }})();"""


class WalkFailed(Exception):
    pass


class Diagnosis:
    """With --diagnose: every error of the app in order, with the step it happened in and the body of failed responses."""

    def __init__(self):
        self.events: list[dict] = []
        self.step = "start"
        self.pending: list[tuple] = []

    def enter(self, number: int, action: str, step: dict) -> None:
        self.drain()
        self.step = f"step {number} {action} {step.get(action, '')}".rstrip()

    def add(self, kind: str, detail: str) -> None:
        self.events.append({"step": self.step, "kind": kind, "detail": detail})

    def response(self, response) -> None:
        if response.status >= 400:
            self.pending.append((self.step, response))

    def failed(self, request) -> None:
        self.add("failed", f"{request.method} {address(request.url)}: {request.failure}")

    def drain(self) -> None:
        """Bodies are read outside the event handlers; a body the browser has dropped stays empty."""
        pending, self.pending = self.pending, []
        for step, response in pending:
            try:
                body = response.text()[:2000]
            except (PlaywrightError, UnicodeDecodeError):
                body = ""
            request = response.request
            # the connector call behind the runtime's gateway, when the runtime names it; never other headers: they hold tokens
            inner = request.headers.get("x-ms-request-url", "")
            inner = f" for {request.headers.get('x-ms-request-method', '')} {address(inner)}" if inner else ""
            self.events.append({"step": step, "kind": "http", "detail": f"{response.status} {request.method} {address(response.url)}{inner}", "body": body})


def address(url: str) -> str:
    """Host and path without the query: it may hold tokens."""
    parts = urlsplit(url)
    return f"{parts.netloc}{parts.path}"


def found(page, name: str) -> list[tuple]:
    """Visible instances of a control across all frames with their boxes relative to the window; the runtime may
    render in a frame."""
    out = []
    for frame in page.frames:
        try:
            loc = frame.locator(f'[data-control-name={json.dumps(name)}]')
            for i in range(loc.count()):
                box = loc.nth(i).bounding_box()
                if box and box["width"] > 0 and box["height"] > 0:
                    out.append((loc.nth(i), box))
        except PlaywrightError:
            continue  # frame replaced during navigation
    return out


def boxes(page, name: str) -> list[dict]:
    return [box for _, box in found(page, name)]


def element(page, name: str, nth: int, timeout: float):
    locate(page, name, nth, timeout)
    return found(page, name)[nth][0]


def visible_part(control) -> dict:
    """The visible rectangle of a control relative to the window, and which share of the control it is."""
    whole = control.bounding_box()
    part = control.evaluate(EXPOSED)
    return {"x": part["x"] + whole["x"] - part["fullX"], "y": part["y"] + whole["y"] - part["fullY"],
            "width": part["width"], "height": part["height"], "ratio": part["ratio"]}


def app_area(page) -> dict | None:
    """The frame the app renders in. The player around it shows the signed-in user's name and photo, where no mask
    reaches (PAPPS-20261103-WIN-05); a mock-up without a frame has no player."""
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            if frame.locator("[data-control-name]").count():
                box = frame.frame_element().bounding_box()
                if box:
                    return box
        except PlaywrightError:
            continue
    return None


def cut_to(box: dict, area: dict | None, size: dict) -> dict:
    """The box cut to the app area and the window."""
    left, top = max(box["x"], area["x"] if area else 0, 0), max(box["y"], area["y"] if area else 0, 0)
    right = min(box["x"] + box["width"], area["x"] + area["width"] if area else size["width"], size["width"])
    bottom = min(box["y"] + box["height"], area["y"] + area["height"] if area else size["height"], size["height"])
    return {"x": left, "y": top, "width": max(right - left, 1), "height": max(bottom - top, 1)}


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


def settle(page, timeout: float) -> float:
    """Wait until the visible controls and their text stop changing; returns the moment of the last change."""
    deadline = time.monotonic() + timeout
    last, since = None, time.monotonic()
    while time.monotonic() < deadline:
        state = [(c["name"], round(c["x"]), round(c["y"]), round(c["w"]), round(c["h"]), c["text"]) for c in scan(page)]
        if state != last:
            last, since = state, time.monotonic()
        elif time.monotonic() - since >= QUIET:
            return since
        page.wait_for_timeout(250)
    return since


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


def shown_texts(page, name: str) -> list[str]:
    """What the visible instances of a control show: the value of a field, else the text."""
    script = """el => { const f = el.matches('input,textarea,select') ? el : el.querySelector('input,textarea,select');
                        return f ? f.value : (el.innerText || ''); }"""
    out = []
    for frame in page.frames:
        try:
            loc = frame.locator(f'[data-control-name={json.dumps(name)}]')
            for i in range(loc.count()):
                box = loc.nth(i).bounding_box()
                if box and box["width"] > 0 and box["height"] > 0:
                    out.append(loc.nth(i).evaluate(script))
        except PlaywrightError:
            continue
    return out


def verify(page, walk: dict, step: dict, number: int, label: str, folder: Path, rep: Report, record: dict,
           mask_seen: set, timeout: float) -> None:
    """A value may arrive late, for example from a flow, so look again until `within`. A miss is recorded with a picture
    and the walk goes on, so one run shows all deviations."""
    deadline = time.monotonic() + float(step.get("within", 30))
    while True:
        met, found = W.expectation(step, shown_texts(page, step["expect"]))
        if met or time.monotonic() >= deadline:
            break
        page.wait_for_timeout(500)
    kind = next(k for k in W.EXPECTATIONS if k in step)
    title = f"{label} step {number}" + (f" ({step['scenario']})" if step.get("scenario") else "")
    what = f"{step['expect']} {kind} {step[kind]!r}"
    entry = {"viewport": label, "step": number, "scenario": step.get("scenario", ""), "expect": what, "met": met, "found": found}
    if met:
        rep.ok(f"{title}: {what}")
    else:
        entry["file"] = str(folder / take(page, walk, {"shot": f"deviation-{number}"}, folder, mask_seen, timeout)["file"])
        rep.error(f"{title}: {what}, {found}; picture {entry['file']}")
    record["expects"].append(entry)


def wait_for(page, name: str, timeout: float, refresh: str = "") -> float:
    """Wait for content; on an empty result press refresh and look again. A failed wait stops the walk, so no empty picture."""
    limit = timeout
    for attempt in range(3 if refresh else 1):
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            if has_content(page, name):
                return settle(page, timeout)
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
    box = locate(page, name, nth, timeout)
    if disabled_at(page, name, box):
        raise WalkFailed(f"control {name} is disabled here, so this session may not do this step")
    page.mouse.click(*centre(box))


def type_into(page, name: str, nth: int, value: str, timeout: float) -> None:
    """Fill the control's own input and check it: Ctrl+A after a click beside the input selected the whole page
    (PAPPS-20261103-WIN-06)."""
    box = locate(page, name, nth, timeout)
    if disabled_at(page, name, box):
        raise WalkFailed(f"control {name} is disabled here, so this session may not do this step")
    control = found(page, name)[nth][0]
    field = control if control.evaluate("el => el.matches('input,textarea')") else \
        control.locator("input:not([type=hidden]),textarea").first
    if not field.count():
        raise WalkFailed(f"control {name} has no input field to type into")
    field.fill(value)
    if field.input_value() != value:
        raise WalkFailed(f"control {name} shows {field.input_value()!r} after typing {value!r}")
    field.press("Tab")  # OnChange fires when the field loses the focus


def disabled_at(page, name: str, box: dict) -> bool:
    script = """el => el.matches('[disabled],[aria-disabled="true"]')
                      || el.querySelector('button[disabled],input[disabled],[aria-disabled="true"]') !== null"""
    for frame in page.frames:
        try:
            loc = frame.locator(f'[data-control-name={json.dumps(name)}]')
            for i in range(loc.count()):
                found = loc.nth(i).bounding_box()
                if found and (found["x"], found["y"]) == (box["x"], box["y"]) and loc.nth(i).evaluate(script):
                    return True
        except PlaywrightError:
            continue
    return False


def prove_role(page, walk: dict, record: dict, timeout: float) -> None:
    """No picture from the wrong session: single sign-on may quietly log in the user's own account."""
    role = walk.get("role")
    if not role:
        return
    identity = role["identity"]
    deadline = time.monotonic() + timeout
    while True:
        met, found = W.expectation(identity, shown_texts(page, identity["control"]))
        if met:
            record["role"] = role["name"]
            return
        if time.monotonic() >= deadline:
            raise WalkFailed(f"this session is not role {role['name']}: {identity['control']} {found}. "
                             "The user signs in with the role's account in the window of this profile")
        page.wait_for_timeout(500)


def take(page, walk: dict, step: dict, folder: Path, mask_seen: set, timeout: float, strict: bool = True) -> dict:
    """A picture of the app area only, without text selection, frames on the visible part of each marked control.
    Strict, in the viewport of the guide's pictures, a mark less than 97 % visible stops the walk; else it is a hint."""
    marked = [(W.mark_parts(mark)[:2]) for mark in step.get("marks", [])]
    for name, nth in marked:
        element(page, name, nth, timeout).evaluate(SCROLL_INTO_VIEW)
    if marked:
        settle(page, timeout)
    items, marks, cut = [], [], []
    for name in walk.get("mask", []):
        for box in boxes(page, name):
            mask_seen.add(name)
            items.append({"x": box["x"], "y": box["y"], "w": box["width"], "h": box["height"]})
    for number, (name, nth) in enumerate(marked, 1):
        part = visible_part(element(page, name, nth, timeout))
        if part["ratio"] < 0.97:
            hint = f"mark {name}: only {part['ratio']:.0%} of it is visible"
            if strict:
                raise WalkFailed(f"{hint}; scroll first or split the shot")
            cut.append(hint)
        items.append({"x": part["x"], "y": part["y"], "w": part["width"], "h": part["height"], "n": number})
        marks.append({"control": name, "nth": nth, **{k: round(part[k], 1) for k in ("x", "y", "width", "height")}})
    for frame in page.frames:
        try:
            frame.evaluate(CLEAR_SELECTION)
        except PlaywrightError:
            continue
    page.evaluate(OVERLAY, [items, walk.get("markColor", "#c00000")])
    target = folder / f"{step['shot']}.png"
    area, size = app_area(page), page.viewport_size
    clip = dict(area) if area else {"x": 0, "y": 0, **size}
    if step.get("crop"):
        box = locate(page, step["crop"], 0, timeout)
        clip = {"x": box["x"] - 12, "y": box["y"] - 12, "width": box["width"] + 24, "height": box["height"] + 24}
    page.screenshot(path=str(target), clip=cut_to(clip, area, size))
    page.evaluate("() => document.getElementById('ppp-overlay').remove()")
    return {"file": target.name, "marks": marks, "cut": cut}


def present(page, walk: dict, step: dict, action: str, timeout: float) -> None:
    """For a video: the step's text as a caption with time to read it, and a ring where the click lands."""
    if step.get("text"):
        text = step["text"].replace("**", "")
        page.evaluate(CAPTION, text)
        page.wait_for_timeout(int(max(2.0, len(text) / 15) * 1000))
    if action in ("click", "type", "hover"):
        box = locate(page, step[action], step.get("nth", 0), timeout)
        page.evaluate(POINTER, [*centre(box), walk.get("markColor", "#c00000")])
        page.wait_for_timeout(700)


def pause_on_marks(page, walk: dict, step: dict, timeout: float) -> None:
    items = []
    for number, mark in enumerate(step.get("marks", []), 1):
        name, nth, _ = W.mark_parts(mark)
        box = locate(page, name, nth, timeout)
        items.append({"x": box["x"], "y": box["y"], "w": box["width"], "h": box["height"], "n": number})
    page.evaluate(OVERLAY, [items, walk.get("markColor", "#c00000")])
    page.wait_for_timeout(2500)
    page.evaluate("() => document.getElementById('ppp-overlay').remove()")


def timed(record: dict, viewport: str, what: str, seconds: float, requests: dict, asked: int = 0) -> None:
    record["timings"].append({"viewport": viewport, "what": what, "seconds": round(max(seconds, 0), 1),
                              "requests": requests["count"] - asked})


def run_steps(page, walk: dict, size: list[int], folder: Path, rep: Report, record: dict, mask_seen: set, timeout: float,
              diagnosis: Diagnosis | None, requests: dict, started: float, work: Path, video: bool) -> None:
    ready = walk["ready"]
    label = f"{size[0]}x{size[1]}"
    done = wait_for(page, ready["control"], timeout, ready.get("refresh", ""))
    timed(record, label, "start", done - started, requests)
    prove_role(page, walk, record, timeout)
    for number, step in enumerate(walk["steps"], 1):
        action = W.action_of(step)
        begun, asked = time.monotonic(), requests["count"]
        if diagnosis:
            diagnosis.enter(number, action, step)
        try:
            if video:
                present(page, walk, step, action, timeout)
            if action == "wait":
                wait_for(page, step["wait"], timeout)
            elif action == "click":
                click(page, step["click"], step.get("nth", 0), timeout)
            elif action == "hover":
                page.mouse.move(*centre(locate(page, step["hover"], step.get("nth", 0), timeout)))
            elif action == "type":
                type_into(page, step["type"], step.get("nth", 0), str(step["value"]), timeout)
            elif action == "key":
                page.keyboard.press(step["key"])
            elif action == "scroll":
                page.mouse.move(*centre(locate(page, step["scroll"], step.get("nth", 0), timeout)))
                page.mouse.wheel(0, step.get("by", 400))
            done = settle(page, timeout)
            mask_seen.update(n for n in walk.get("mask", []) if boxes(page, n))
            if action in ("click", "type", "key", "wait"):
                timed(record, label, f"step {number} {action} {step.get(action, '')}".rstrip(), done - begun, requests, asked)
            if action == "expect":
                verify(page, walk, step, number, label, work, rep, record, mask_seen, timeout)
            elif action == "shot" and video:
                pause_on_marks(page, walk, step, timeout)
            elif action == "shot":
                shot = take(page, walk, step, folder, mask_seen, timeout, strict=size == W.viewports(walk)[0])
                for hint in shot["cut"]:
                    rep.warn(f"{label} {step['shot']}: {hint}")
                controls = scan(page)
                findings = W.layout_findings(controls, size, walk.get("ignore", [])) if step.get("check", True) else []
                for finding in findings:
                    rep.warn(f"{label} {step['shot']}: {finding}")
                record["shots"].append({"viewport": label, "id": step["shot"], "file": str(folder / shot["file"]),
                                        "marks": shot["marks"], "findings": findings,
                                        "controls": sorted({c["name"] for c in controls})})
        except WalkFailed as ex:
            raise WalkFailed(f"step {number} ({action}): {ex}")


def report_timings(record: dict, work: Path, rep: Report) -> None:
    for t in record["timings"]:
        if t["what"] == "start" or t["seconds"] >= 1:
            rep.info(f"{t['viewport']} {t['what']}: {t['seconds']:.1f} s, {t['requests']} requests")
    try:
        before = json.loads((work / "previous" / "report.json").read_text(encoding="utf-8")).get("timings", [])
    except (OSError, ValueError):
        return
    for line in W.slower(record["timings"], before):
        rep.warn(f"slower: {line}")


def keep_last_run(folder: Path, work: Path) -> None:
    """The pictures of the last complete run become the baseline; an aborted run leaves the baseline as it is."""
    report = folder / "report.json"
    try:
        last = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not last.get("complete"):
        return
    previous = work / "previous"
    shutil.rmtree(previous, ignore_errors=True)
    previous.mkdir(parents=True)
    for shot in last["shots"]:
        target = previous / shot["viewport"] / f"{shot['id']}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        if Path(shot["file"]).is_file():
            shutil.copyfile(shot["file"], target)
    shutil.copyfile(report, previous / "report.json")


def compare(context, work: Path, record: dict, rep: Report) -> None:
    """Compare each picture with the last complete run, in the browser, so that no image package is needed. The grey-out
    diff shows changed pixels in red. Changes are expected in a package: they say where to look, not that something is wrong."""
    if not (work / "previous").is_dir():
        return
    page = context.new_page()
    same = 0
    shutil.rmtree(work / "diff", ignore_errors=True)
    for shot in record["shots"]:
        before = work / "previous" / shot["viewport"] / f"{shot['id']}.png"
        title = f"{shot['viewport']} {shot['id']}"
        if not before.is_file():
            rep.info(f"{title}: new picture")
            continue
        encoded = [base64.b64encode(p.read_bytes()).decode() for p in (before, Path(shot["file"]))]
        result = page.evaluate(COMPARE, encoded)
        if result.get("size"):
            rep.info(f"{title}: size changed, {result['size']}")
        elif result["percent"]:
            diff = work / "diff" / shot["viewport"] / f"{shot['id']}.png"
            diff.parent.mkdir(parents=True, exist_ok=True)
            diff.write_bytes(base64.b64decode(result["diff"]))
            x, y, w, h = result["box"]
            shot["changed"] = {"percent": round(result["percent"], 2), "box": result["box"], "diff": str(diff)}
            rep.info(f"{title}: {result['percent']:.2f} % changed, area {w}x{h} at {x},{y}; {diff}")
        else:
            same += 1
    page.close()
    rep.info(f"compared with the last complete run: {same} pictures unchanged")


def sheets(context, work: Path, record: dict, rep: Report) -> None:
    """Overviews of the run, up to six pictures each per viewport, outside git."""
    shutil.rmtree(work / "sheets", ignore_errors=True)
    by_viewport: dict = {}
    for shot in record["shots"]:
        by_viewport.setdefault(shot["viewport"], []).append(shot)
    page = context.new_page()
    for viewport, shots in by_viewport.items():
        for start in range(0, len(shots), 6):
            part = shots[start:start + 6]
            encoded = [base64.b64encode(Path(s["file"]).read_bytes()).decode() for s in part]
            file = work / "sheets" / f"{viewport}-{start // 6 + 1}.png"
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(base64.b64decode(page.evaluate(SHEET, [encoded, [s["id"] for s in part]])))
            rep.info(f"overview {file}: {', '.join(s['id'] for s in part)}")
    page.close()


def main(options: dict) -> int:
    path = Path(options["walk"])
    walk = W.load(path)
    folder = Path(options["out"])
    folder.mkdir(parents=True, exist_ok=True)
    timeout = float(options["timeout"])
    work = Path(options["work"])
    work.mkdir(parents=True, exist_ok=True)
    keep_last_run(folder, work)
    rep = Report(f"ppp walk: {W.name_of(path)}")
    record = {"walk": W.name_of(path), "shots": [], "expects": [], "timings": [], "console": [], "http": [],
              "screens": options.get("screens", {})}  # what the pictures show; ppp check names the walk when one changes
    mask_seen: set = set()
    aborted = False
    diagnosis = Diagnosis() if options.get("diagnosis") else None
    video = bool(options.get("video"))
    first = {"width": W.viewports(walk)[0][0], "height": W.viewports(walk)[0][1]}
    raw_video = folder / "raw"

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                options["profile"], channel=options["channel"], headless=options["headless"], viewport=first,
                **({"record_video_dir": str(raw_video), "record_video_size": first} if video else {}))
        except PlaywrightError as ex:
            hint = f' Recording needs ffmpeg: "{sys.executable}" -m playwright install ffmpeg, after the user agreed.' if "ffmpeg" in str(ex) else ""
            print(f"ERROR: the browser did not start: {str(ex).splitlines()[0]}{hint} Is a window of this profile still open?", file=sys.stderr)
            return 2
        if video and walk.get("mask"):
            context.add_init_script(mask_script(walk["mask"]))
        page = context.pages[0] if context.pages else context.new_page()
        page.on("console", lambda m: record["console"].append(m.text[:300]) if m.type == "error" else None)
        page.on("pageerror", lambda e: record["console"].append(str(e)[:300]))

        def note(response):
            if response.status >= 400:
                record["http"].append(f"{response.status} {address(response.url)}"[:300])
        page.on("response", note)
        requests = {"count": 0}

        def count(_request):
            requests["count"] += 1
        page.on("request", count)
        page.on("requestfailed", lambda r: record["http"].append(f"failed {address(r.url)}"[:300]))
        if diagnosis:
            page.on("console", lambda m: diagnosis.add("console", m.text[:2000]) if m.type == "error" else None)
            page.on("pageerror", lambda e: diagnosis.add("pageerror", str(e)[:2000]))
            page.on("response", diagnosis.response)
            page.on("requestfailed", diagnosis.failed)
        try:
            for number, size in enumerate(W.viewports(walk)):
                if number and W.writes(walk):
                    rep.info(f"{size[0]}x{size[1]} skipped: this walk writes data, it runs once")
                    continue
                if number and video:
                    break  # one recording, in the first viewport
                target = folder if not number else folder / f"{size[0]}x{size[1]}"
                target.mkdir(parents=True, exist_ok=True)
                page.set_viewport_size({"width": size[0], "height": size[1]})
                started = time.monotonic()
                requests["count"] = 0
                page.goto(options["url"], wait_until="domcontentloaded", timeout=timeout * 1000)
                run_steps(page, walk, size, target, rep, record, mask_seen, timeout, diagnosis, requests, started, work, video)
            if not video:
                compare(context, work, record, rep)
                sheets(context, work, record, rep)
        except (WalkFailed, PlaywrightError) as ex:
            work.mkdir(parents=True, exist_ok=True)
            failed = work / "failed.png"  # without masks, so outside git whatever the walk's "out" says
            try:
                page.screenshot(path=str(failed))
                rep.info(f"state at the failure: {failed}")
            except PlaywrightError:
                pass
            rep.error(str(ex).splitlines()[0])
            aborted = True
        finally:
            if diagnosis:
                diagnosis.drain()
            context.close()
            recorded = Path(page.video.path()) if video else None

    if video:
        target = folder / f"{W.name_of(path)}.webm"
        shutil.move(str(recorded), target)
        shutil.rmtree(raw_video, ignore_errors=True)
        rep.info(f"recording: {target}")
    record["complete"] = not aborted
    report_timings(record, work, rep)
    if not aborted:
        for name in sorted(set(walk.get("mask", [])) - mask_seen):
            rep.error(f"mask {name} was never found; the pictures may show what it should cover")
    for kind, title in (("console", "console errors"), ("http", "failed requests")):
        if record[kind]:
            rep.warn(f"{len(record[kind])} {title}, first: {record[kind][0]}")
    if W.role_name(walk) and not aborted:
        rep.ok(f"session proven as role {W.role_name(walk)}")
    if W.writes(walk) and walk.get("testData"):
        rep.info(f"test data carries the mark {walk['testData'].get('mark')}; remove it: {walk['testData'].get('cleanup')}")
    if diagnosis:
        file = Path(options["diagnosis"])
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(diagnosis.events, ensure_ascii=False, indent=1), encoding="utf-8")
        for event in diagnosis.events[:10]:
            rep.info(f"{event['step']}: {event['kind']} {event['detail'][:200]} {event.get('body', '')[:200]}".rstrip())
        rep.info(f"{len(diagnosis.events)} errors of the app in {file}")
    (folder / "report.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    rep.info(f"{len(record['shots'])} pictures and report.json in {folder}")
    print(rep.text())
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(json.loads(sys.argv[1])))
