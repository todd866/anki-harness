"""Run one scenario inside a real Anki, with no window, and write what it observed.

    <an Anki version's python> -m harness.inproc <scenario> <out-dir> [collection.anki2]

The process IS Anki: it starts aqt on a throwaway base folder, waits for the collection,
then steps the scenario on Qt's main thread. A scenario is a generator. It yields a number
(seconds to wait) or a function (wait until it returns true). It records observations and
checks through the Session it is given. It never opens your own Anki profile.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import tempfile
import time
import traceback

WAIT_TIMEOUT_S = 15


class Inconclusive(Exception):
    """The scenario could not drive Anki far enough to say anything (its own control failed).
    The runner retries; nothing is concluded from such a run."""


class Session:
    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        self.observations: dict = {}
        self.checks: list = []
        self.log: list = []
        self.t0 = time.time()

    # -- recording -------------------------------------------------------
    def observe(self, name: str, value) -> None:
        """Something to compare between versions. Keep values small and deterministic."""
        self.observations[name] = value

    def check(self, name: str, ok: bool, detail: str = "", known: str = "") -> None:
        """Something that must hold on every version. `known` names an open upstream issue this
        check is expected to fail on: the runner reports it apart from new failures, and says so
        when it starts passing."""
        self.checks.append({"name": name, "ok": bool(ok), "detail": detail, "known": known})

    def inconclusive(self, reason: str) -> None:
        raise Inconclusive(reason)

    def note(self, text: str) -> None:
        self.log.append(f"{time.time() - self.t0:6.2f}s {text}")

    # -- Anki ------------------------------------------------------------
    @property
    def mw(self):
        import aqt

        return aqt.mw

    @property
    def col(self):
        return self.mw.col

    def key(self, key, modifier=None, target=None) -> None:
        """A real Qt key press, delivered the way a keyboard delivers it."""
        from aqt.qt import Qt
        from PyQt6.QtTest import QTest

        widget = target or self.mw
        QTest.keyClick(widget, key, modifier or Qt.KeyboardModifier.NoModifier)

    def type(self, widget, text: str) -> None:
        """Real key presses for each character of `text`, sent to `widget`."""
        from PyQt6.QtTest import QTest

        QTest.keyClicks(widget, text)

    def js(self, web, expression: str, into: str) -> None:
        """Evaluate in one of Anki's web views; the result lands in self.scratch[into]."""
        self.scratch.pop(into, None)
        web.evalWithCallback(expression, lambda value: self.scratch.__setitem__(into, value))

    scratch: dict = {}

    def have(self, key: str):
        return lambda: key in self.scratch

    def screenshot(self, name: str) -> None:
        self.mw.grab().save(os.path.join(self.out_dir, f"{name}.png"))

    def undo_label(self) -> str:
        return self.col.undo_status().undo

    def redo_label(self) -> str:
        return self.col.undo_status().redo

    def make_image(self, name: str = "harness.png", width: int = 600, height: int = 400) -> str:
        """A plain test image on disk: white, with a grid so masks have something to sit on."""
        from aqt.qt import QColor, QImage, QPainter

        image = QImage(width, height, QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        painter = QPainter(image)
        painter.setPen(QColor("#888888"))
        for x in range(0, width, 50):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height, 50):
            painter.drawLine(0, y, width, y)
        painter.end()
        path = os.path.join(self.out_dir, name)
        image.save(path)
        return path

    def add_image_occlusion(self, image_path: str, rects: list[tuple[float, float, float, float]]) -> int:
        """An image-occlusion note with one mask per rect (left, top, width, height as fractions)."""
        col = self.col
        col.add_image_occlusion_notetype()
        notetype = next(m for m in col.models.all() if m.get("originalStockKind") == 6 or "Image Occlusion" in m["name"])
        occlusions = "".join(
            f"{{{{c{i + 1}::image-occlusion:rect:left={l}:top={t}:width={w}:height={h}}}}}" for i, (l, t, w, h) in enumerate(rects)
        )
        before = set(col.find_notes(""))
        col.add_image_occlusion_note(notetype_id=notetype["id"], image_path=image_path, occlusions=occlusions, header="harness", back_extra="", tags=[])
        return (set(col.find_notes("")) - before).pop()

    def input_widget(self, web):
        """The widget that actually receives input for a web view. Chromium's render widget is
        created after the page loads and is replaced when the page is, so ask each time."""
        from PyQt6.QtWidgets import QWidget

        proxy = web.focusProxy()
        if proxy is not None and proxy is not web:
            return proxy
        children = [c for c in web.findChildren(QWidget) if c.isVisible() and c.width() > 0]
        return children[-1] if children else web

    def mouse(self, widget, kind: str, x: float, y: float) -> None:
        """A real Qt mouse event at widget coordinates. kind: move, press, release."""
        from aqt.qt import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtWidgets import QApplication

        types = {"move": QEvent.Type.MouseMove, "press": QEvent.Type.MouseButtonPress, "release": QEvent.Type.MouseButtonRelease}
        button = Qt.MouseButton.NoButton if kind == "move" and not getattr(self, "_down", False) else Qt.MouseButton.LeftButton
        buttons = Qt.MouseButton.LeftButton if (kind == "press" or (kind == "move" and getattr(self, "_down", False))) else Qt.MouseButton.NoButton
        if kind == "press":
            self._down = True
        if kind == "release":
            self._down = False
        local = QPointF(x, y)
        event = QMouseEvent(types[kind], local, widget.mapToGlobal(local), button if kind != "move" else Qt.MouseButton.NoButton, buttons, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(widget, event)

    def add_cloze(self, deck: str, texts: list[str], tags: list[str] | None = None) -> list:
        col = self.col
        notetype = next(m for m in col.models.all() if m["type"] == 1)  # the stock cloze type, whatever its name
        deck_id = col.decks.id(deck)
        notes = []
        for text in texts:
            note = col.new_note(notetype)
            note.fields[0] = text
            note.tags = list(tags or [])
            col.add_note(note, deck_id)
            notes.append(note)
        return notes


def main() -> None:
    scenario_name, out_dir = sys.argv[1], sys.argv[2]
    collection = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(out_dir, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["ANKI_NOHIGHDPI"] = "1"
    # Anki 25.09 (Qt 6.9) segfaults offscreen on the GPU path; later versions run either way.
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
    port = os.environ.get("HARNESS_CDP_PORT")
    if port:
        os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = f"127.0.0.1:{port}"
    import faulthandler

    faulthandler.dump_traceback_later(int(os.environ.get("HARNESS_HARD_TIMEOUT_S", "120")), exit=True)

    base = tempfile.mkdtemp(prefix="anki-harness-base-")
    if collection:
        profile = os.path.join(base, "User 1")
        os.makedirs(profile)
        shutil.copy(collection, os.path.join(profile, "collection.anki2"))

    import anki.buildinfo
    import aqt
    from aqt.profiles import ProfileManager
    from aqt.qt import QTimer

    # The first-run language chooser is a modal dialog with nobody to answer it.
    ProfileManager.setDefaultLang = lambda self, idx: self.meta.__setitem__("defaultLang", "en_US")
    session = Session(out_dir)
    result = {"scenario": scenario_name, "version": anki.buildinfo.version, "status": "started"}
    scenario = importlib.import_module(f"harness.scenarios.{scenario_name}")

    def finish(status: str, error: str = "") -> None:
        result.update(status=status, error=error, observations=session.observations, checks=session.checks, log=session.log)
        with open(os.path.join(out_dir, "result.json"), "w") as handle:
            json.dump(result, handle, indent=1, default=str)
        os._exit(0 if status == "ran" else 1)  # no close-time sync, backup or dialogs

    app = aqt._run(["anki", "-b", base, "-l", "en"], exec=False)
    state = {"gen": None, "waiting": None, "since": 0.0}

    def step() -> None:
        try:
            if state["gen"] is None:
                if not (aqt.mw and aqt.mw.col):
                    QTimer.singleShot(200, step)
                    return
                state["gen"] = scenario.run(session)
            waiting = state["waiting"]
            if waiting is not None:
                if not waiting():
                    if time.time() - state["since"] > WAIT_TIMEOUT_S:
                        session.check("wait completed", False, f"timed out waiting: {getattr(waiting, '__name__', waiting)}")
                        state["waiting"] = None  # carry on; the scenario records what it can
                    else:
                        QTimer.singleShot(100, step)
                        return
                state["waiting"] = None
            wanted = next(state["gen"])
            if callable(wanted):
                state["waiting"], state["since"] = wanted, time.time()
                QTimer.singleShot(50, step)
            else:
                QTimer.singleShot(int(float(wanted or 0) * 1000), step)
        except StopIteration:
            finish("ran")
        except Inconclusive as reason:
            finish("inconclusive", str(reason))
        except Exception:
            finish("error", traceback.format_exc()[-3000:])

    QTimer.singleShot(300, step)
    app.exec()


if __name__ == "__main__":
    main()
