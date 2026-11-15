"""Review three cards with real key presses, then undo one answer.

Covers the path a learner uses hundreds of times a day: Space shows the answer, a number
grades, and Undo puts the card back.
"""
from aqt.qt import Qt


def run(s):
    s.add_cloze("harness", [f"Fact {i}: the answer is {{{{c1::value {i}}}}}." for i in range(3)])
    s.col.decks.select(s.col.decks.id("harness"))
    s.mw.moveToState("review")
    yield lambda: s.mw.state == "review" and s.mw.reviewer.card is not None
    yield 0.6
    reviewer = s.mw.reviewer
    first = reviewer.card.id
    s.js(reviewer.web, "document.getElementById('qa').innerText", "front")
    yield s.have("front")
    s.observe("front text", s.scratch["front"])
    s.check("question hides the answer", "value 0" not in s.scratch["front"], s.scratch["front"])

    s.key(Qt.Key.Key_Space)
    yield lambda: reviewer.state == "answer"
    s.check("Space shows the answer", reviewer.state == "answer", reviewer.state)
    yield 0.4
    s.js(reviewer.web, "document.getElementById('qa').innerText", "back")
    yield s.have("back")
    s.observe("back text", s.scratch["back"])

    s.key(Qt.Key.Key_3)
    yield lambda: reviewer.card is not None and reviewer.card.id != first
    s.check("3 grades and moves to the next card", reviewer.card.id != first)
    s.observe("revlog after one answer", s.col.db.all("select ease, type from revlog order by id"))
    s.observe("undo label after answer", s.undo_label())

    s.key(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    yield lambda: reviewer.card is not None and reviewer.card.id == first
    s.check("Undo brings the answered card back", reviewer.card.id == first)
    s.observe("revlog rows after undo", s.col.db.scalar("select count() from revlog"))
    s.observe("first card queue after undo", s.col.db.scalar("select queue from cards where id = ?", first))
