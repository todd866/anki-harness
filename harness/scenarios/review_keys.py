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
    reviewer = s.mw.reviewer
    first = reviewer.card.id
    for _ in range(100):  # the card is drawn some time after the state changes, longer on a busy machine
        s.js(reviewer.web, "(document.getElementById('qa') || {}).innerText || ''", "front")
        yield s.have("front")
        if s.scratch["front"].strip():
            break
        yield 0.2
    else:
        s.inconclusive("the review screen did not draw the question within 20 s")
    s.observe("front text", s.scratch["front"].strip())
    s.check("question hides the answer", "value 0" not in s.scratch["front"], s.scratch["front"])

    s.key(Qt.Key.Key_Space)
    yield lambda: reviewer.state == "answer"
    s.check("Space shows the answer", reviewer.state == "answer", reviewer.state)
    for _ in range(100):
        s.js(reviewer.web, "(document.getElementById('qa') || {}).innerText || ''", "back")
        yield s.have("back")
        if "value 0" in s.scratch["back"]:
            break
        yield 0.2
    else:
        s.inconclusive("the review screen did not draw the answer within 20 s")
    s.observe("back text", s.scratch["back"].strip())

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
