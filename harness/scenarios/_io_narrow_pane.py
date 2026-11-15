"""Shared body for the narrow-pane image-occlusion scenarios (not a scenario itself).

Upstream #3267 reports masks disappearing after an occlusion note is edited. The editor
drops any shape under 5 px when it saves, and it measures in canvas pixels. The canvas is
sized to the editor pane when the mask editor mounts, so a mask that clears 5 px in a wide
window can fall under it when the same note is opened in a narrow pane.

The control comes first: in a wide window, moving the other mask and saving keeps both.
Then the note is reopened in a narrow pane and the same edit is made.
"""
import json
import re

import aqt

CANVAS = """(() => { const c = globalThis.canvas; if (!c || !c.getObjects) return null;
  const el = document.querySelector('canvas.upper-canvas') || document.querySelector('canvas');
  if (!el) return null;
  const r = el.getBoundingClientRect(); const v = c.viewportTransform;
  const masks = c.getObjects().filter(o => o.id !== 'boundingBox').map(o => { const m = o.calcTransformMatrix();
    return {x: Math.round(m[4] * v[0] + v[4] + r.left), y: Math.round(m[5] * v[3] + v[5] + r.top),
            w: Math.round(o.width * o.scaleX * v[0] * 10) / 10, canvasW: Math.round(o.width * o.scaleX * 10) / 10}; }).sort((a, b) => b.w - a.w);
  const box = c.getObjects().find(o => o.id === 'boundingBox');
  return JSON.stringify({masks, image: box ? Math.round(box.width * box.scaleX) : null}); })()"""
DRAG_PX = 20


def mask_count(field: str) -> int:
    return len(re.findall(r"image-occlusion:", field))


def run_with(s, thin: float, known: str = ""):
    """`thin` is the small mask's width as a fraction of the image width."""
    image = s.make_image()
    nid = s.add_image_occlusion(image, [(0.1, 0.1, 0.2, 0.2), (0.6, 0.6, thin, 0.2)])
    field = lambda: s.col.get_note(nid).fields[0]
    s.observe("masks at start", mask_count(field()))
    cards_at_start = len(s.col.find_cards(f"nid:{nid}"))

    browser = aqt.dialogs.open("Browser", s.mw)
    browser.resize(1500, 950)
    yield 0.8
    browser.search_for(f"nid:{nid}")
    yield 0.8
    browser.table.select_single_card(s.col.find_cards(f"nid:{nid}")[0])
    web = browser.editor.web

    def canvas():
        s.js(web, CANVAS, "canvas")
        yield s.have("canvas")
        return json.loads(s.scratch["canvas"]) if s.scratch.get("canvas") else None

    def settled():
        state, previous = None, None
        for _ in range(40):
            state = yield from canvas()
            if state and len(state["masks"]) >= 1 and state == previous:
                return state
            previous = state
            yield 0.3
        return state

    def drag_wide_mask():
        """Drag the wide mask a little, until the canvas shows it moved. Returns True if it did."""
        for _attempt in range(3):
            before = yield from canvas()
            m = before["masks"][0]
            target = s.input_widget(web)
            s.mouse(target, "move", m["x"], m["y"])
            s.mouse(target, "press", m["x"], m["y"])
            for i in range(1, 6):
                s.mouse(target, "move", m["x"] + DRAG_PX * i / 5, m["y"])
            s.mouse(target, "release", m["x"] + DRAG_PX, m["y"])
            yield 0.3
            after = yield from canvas()
            if after["masks"] and after["masks"][0]["x"] - m["x"] > DRAG_PX / 2:
                return True
            yield 0.5
        return False

    def save():
        s.scratch.pop("saved", None)
        browser.editor.call_after_note_saved(lambda: s.scratch.__setitem__("saved", True), keepFocus=True)
        yield s.have("saved")
        yield 0.3

    # Control: wide window.
    wide = yield from settled()
    if not wide or len(wide["masks"]) != 2:
        s.inconclusive(f"mask editor did not show both masks: {wide}")
    s.observe("wide pane: image width on the canvas, thin mask width (canvas px)", [wide["image"], wide["masks"][1]["canvasW"]])
    if not (yield from drag_wide_mask()):
        s.inconclusive("mouse input did not move a mask in the wide window")
    yield 1.0
    yield from save()
    s.observe("masks after an edit in a wide pane", mask_count(field()))
    s.check("control: both masks survive an edit in a wide pane", mask_count(field()) == 2, field())
    if mask_count(field()) != 2:
        return

    # The case: the same edit with the note opened in a narrow editor pane. The canvas is sized
    # when the mask editor mounts, so narrow the pane first and then load the note afresh.
    splitter = browser.form.splitter
    total = sum(splitter.sizes())
    splitter.setSizes([total - 260, 260])
    browser.search_for("nid:1")  # no such note: empties the editor
    yield 0.8
    browser.search_for(f"nid:{nid}")
    yield 0.8
    browser.table.select_single_card(s.col.find_cards(f"nid:{nid}")[0])
    web = browser.editor.web
    yield 1.0
    s.observe("editor pane width", web.width())
    narrow = yield from settled()
    if not narrow or len(narrow["masks"]) != 2:
        s.inconclusive(f"mask editor did not show both masks after narrowing: {narrow}")
    s.observe("narrow pane: image width on the canvas, thin mask width (canvas px)", [narrow["image"], narrow["masks"][1]["canvasW"]])
    if not (yield from drag_wide_mask()):
        s.inconclusive("mouse input did not move a mask in the narrow pane")
    yield 1.0
    yield from save()
    s.observe("masks after the same edit in a narrow pane", mask_count(field()))
    s.observe("cards before and after", [cards_at_start, len(s.col.find_cards(f"nid:{nid}"))])
    s.check("a small mask survives an edit made in a narrow pane", mask_count(field()) == 2, f"the note had 2 masks and now has {mask_count(field())} after another mask was moved", known=known)
    browser.grab().save(s.out_dir + "/browser.png")
