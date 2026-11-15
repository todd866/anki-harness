"""Image occlusion: move one mask, then move two masks selected together, and see what is saved.

Upstream #4223 reports that masks moved or scaled as a multi-selection are not saved. The
single-mask move runs first, in the same editor, as the control: it shows that the drag and
the save path work here, so an unsaved multi-selection is the editor's doing and not ours.

The mask editor does not keep masks in a fixed order, and a drag can fail to register while
its layout is settling (Anki's own end-to-end tests retry for the same reason). So positions
are read fresh before every drag, the leftmost mask is always the one pressed, and a drag is
retried until the canvas shows the move.
"""
import json
import re

import aqt

# Page coordinates of each mask's centre, leftmost first, and what is selected.
CANVAS = """(() => { const c = globalThis.canvas; if (!c || !c.getObjects) return null;
  const el = document.querySelector('canvas.upper-canvas') || document.querySelector('canvas');
  if (!el) return null;
  const r = el.getBoundingClientRect(); const v = c.viewportTransform;
  const masks = c.getObjects().filter(o => o.id !== 'boundingBox').map(o => { const m = o.calcTransformMatrix();
    return [Math.round(m[4] * v[0] + v[4] + r.left), Math.round(m[5] * v[3] + v[5] + r.top)]; }).sort((a, b) => a[0] - b[0]);
  return JSON.stringify({rect: [r.left, r.top, r.width, r.height].map(Math.round), masks,
    active: c.getActiveObject() ? c.getActiveObject().type : null}); })()"""
SELECT_ALL = "(() => { const b = [...document.querySelectorAll('button')].find(b => (b.title || '').startsWith('Select All')); if (b) b.click(); return !!b; })()"
DRAG_PX = 40


def lefts(field: str) -> list[float]:
    """Each mask's left edge as a fraction of the image, sorted, to two places: re-saving
    rounds an untouched mask in the third."""
    return sorted(round(float(x), 2) for x in re.findall(r"left=([0-9.]+)", field))


def run(s):
    image = s.make_image()
    nid = s.add_image_occlusion(image, [(0.1, 0.1, 0.2, 0.2), (0.5, 0.5, 0.2, 0.2)])
    field = lambda: s.col.get_note(nid).fields[0]  # the Occlusion field
    s.observe("masks at start", lefts(field()))

    browser = aqt.dialogs.open("Browser", s.mw)
    browser.resize(1500, 950)
    yield 0.8
    browser.search_for(f"nid:{nid}")
    yield 0.8
    browser.table.select_single_card(s.col.find_cards(f"nid:{nid}")[0])
    web = browser.editor.web
    s.observe("editor", type(browser.editor).__module__)

    def canvas():
        """Generator: read the canvas, returning the parsed state (or None)."""
        s.js(web, CANVAS, "canvas")
        yield s.have("canvas")
        return json.loads(s.scratch["canvas"]) if s.scratch.get("canvas") else None

    # Wait until the mask editor has mounted and its layout has stopped moving.
    state, previous = None, None
    for _ in range(40):
        state = yield from canvas()
        if state and len(state["masks"]) == 2 and state == previous:
            break
        previous = state
        yield 0.3
    s.check("mask editor opened with both masks", bool(state) and len(state["masks"]) == 2, str(state))
    if not state or len(state["masks"]) != 2:
        return

    def drag_leftmost(select_all: bool):
        """Generator: drag the leftmost mask DRAG_PX right until the canvas shows it moved.
        Returns (centres before, centres after)."""
        before = after = None
        for _attempt in range(3):
            if select_all:
                s.js(web, SELECT_ALL, "clicked")
                yield s.have("clicked")
                yield 0.3
            before = yield from canvas()
            x, y = before["masks"][0]
            target = s.input_widget(web)
            s.mouse(target, "move", x, y)
            s.mouse(target, "press", x, y)
            for i in range(1, 6):
                s.mouse(target, "move", x + DRAG_PX * i / 5, y)
            s.mouse(target, "release", x + DRAG_PX, y)
            yield 0.3
            after = yield from canvas()
            if after["masks"][0][0] - before["masks"][0][0] > DRAG_PX / 2:
                break
            yield 0.5
        return before, after

    def save():
        s.scratch.pop("saved", None)
        browser.editor.call_after_note_saved(lambda: s.scratch.__setitem__("saved", True), keepFocus=True)
        yield s.have("saved")
        yield 0.3

    xs = lambda st: [m[0] for m in st["masks"]]

    # Control: one mask.
    before, after = yield from drag_leftmost(select_all=False)
    control_moved = xs(after)[0] - xs(before)[0] > DRAG_PX / 2 and abs(xs(after)[1] - xs(before)[1]) < 3
    if not control_moved:
        s.inconclusive(f"mouse input did not move a mask in three tries: {xs(before)} -> {xs(after)}")
    s.check("control: the dragged mask moved on the canvas", True)
    yield 1.0  # the editor debounces its save
    yield from save()
    after_single = lefts(field())
    s.observe("masks after moving one", after_single)
    # 40 px on a 593 px image is 0.07: the left mask goes from 0.10 to 0.17, the other stays at 0.50
    s.check("control: a single dragged mask is saved", after_single == [0.17, 0.5], str(after_single))

    # The case: both masks selected together.
    before, after = yield from drag_leftmost(select_all=True)
    s.check("both masks are selected together", str(after["active"]).lower() == "activeselection", str(after["active"]))
    both_moved = all(a - b > DRAG_PX / 2 for a, b in zip(xs(after), xs(before)))
    s.check("both masks moved on the canvas", both_moved, f"{xs(before)} -> {xs(after)}")
    if not both_moved:
        s.inconclusive(f"the multi-selection drag did not register: {xs(before)} -> {xs(after)}")
    yield 1.0
    yield from save()
    after_multi = lefts(field())
    s.observe("masks after moving both", after_multi)
    saved = all(b - a > 0.03 for a, b in zip(after_single, after_multi))
    s.check("masks moved as a multi-selection are saved", saved, f"the canvas shows both masks moved, the note still has {after_multi}", known="#4223")
    browser.grab().save(s.out_dir + "/browser.png")
