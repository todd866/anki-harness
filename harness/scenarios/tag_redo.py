"""Known open bugs, upstream #5965 and #5966: tag expansion and the redo queue.

No window needed, but run inside the same Anki so every layer is the shipped one.
"""


def run(s):
    col = s.col
    s.add_cloze("harness", ["Tagged: {{c1::one}}."], tags=["parent::child"])
    yield 0.2
    s.observe("tags", sorted(col.tags.all()))
    # 5965: an operation that is not itself undoable should not throw away a pending redo.
    s.add_cloze("harness", ["Second: {{c1::two}}."])
    col.undo()
    s.observe("redo label after undo", s.redo_label())
    had_redo = bool(s.redo_label())
    col.tags.set_collapsed("parent", collapsed=False)
    s.observe("redo label after expanding a tag", s.redo_label())
    s.check("expanding a tag keeps the pending redo", (not had_redo) or bool(s.redo_label()), "redo was cleared by a tag expansion", known="#5965")
    yield 0.1
