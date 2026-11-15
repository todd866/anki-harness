"""Known open bug, upstream #4311: R or E on a normal deck's overview wipes undo history.

A calibration scenario. The harness is only worth trusting if it sees a bug we know is there.
"""
from aqt.qt import Qt


def run(s):
    s.add_cloze("harness", ["Undo me: {{c1::one}}."])
    deck = s.col.decks.id("harness")
    s.col.decks.select(deck)
    s.observe("undo label before", s.undo_label())
    s.check("adding a note is undoable", bool(s.undo_label()), s.undo_label())
    s.mw.moveToState("overview")
    yield lambda: s.mw.state == "overview"
    yield 0.5
    s.key(Qt.Key.Key_R)
    yield 1.0
    s.observe("undo label after R on a normal deck", s.undo_label())
    s.check("R on a normal deck leaves undo history alone", bool(s.undo_label()), "undo history is empty after pressing R", known="#4311")
    s.observe("notes still present", s.col.db.scalar("select count() from notes"))
