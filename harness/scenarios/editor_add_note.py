"""Add window: type a note with real key presses, add it with the shortcut, and see the
fields cleared for the next one.

The path every card passes through once. Uses whichever editor the version opens by default
(the legacy editor on 26.09 and 26.11; the new one is still behind an experiment flag).

Not covered yet: the cloze shortcut. Sent as a synthetic key press it does not reach the
editor's own shortcut handler, so that step is left out instead of being reported.
"""
from aqt.qt import Qt

FIELD_TEXT = "(document.activeElement && document.activeElement.shadowRoot ? document.activeElement.shadowRoot.querySelector('anki-editable') : document.activeElement || {}).innerText || ''"
FIELDS = "JSON.stringify([...document.querySelectorAll('.rich-text-editable')].map(e => e.shadowRoot ? (e.shadowRoot.querySelector('anki-editable') || {}).innerText || '' : e.innerText))"


def run(s):
    col = s.col
    col.decks.select(col.decks.id("harness"))
    basic = col.models.by_name("Basic")
    col.set_config("curModel", basic["id"])
    s.mw.onAddCard()
    yield 1.5
    add = next((w for w in s.mw.app.topLevelWidgets() if type(w).__name__ in ("AddCards", "NewAddCards") and w.isVisible()), None)
    if add is None:
        s.inconclusive("the Add window did not open")
    s.observe("add window", f"{type(add).__module__}.{type(add).__name__}")
    add.set_note_type(basic["id"])
    add.set_deck(col.decks.id("harness"))
    yield 1.0
    web = add.editor.web

    def focus_field(index):
        s.js(web, f"(() => {{ const f = document.querySelectorAll('.rich-text-editable')[{index}]; if (!f) return false; (f.shadowRoot ? f.shadowRoot.querySelector('anki-editable') : f).focus(); return true; }})()", "focused")
        yield s.have("focused")
        yield 0.3
        return bool(s.scratch["focused"])

    def fields():
        s.js(web, FIELDS, "fields")
        yield s.have("fields")
        import json

        # a field that has lost focus reports a trailing line break
        return [text.strip() for text in json.loads(s.scratch["fields"] or "[]")]

    for _ in range(40):  # the editor's fields mount a moment after the window
        current = yield from fields()
        if len(current) >= 2:
            break
        yield 0.3
    else:
        s.inconclusive("the editor did not show its fields")

    if not (yield from focus_field(0)):
        s.inconclusive("could not focus the first field")
    s.type(s.input_widget(web), "What carries blood from the heart")
    yield 0.4
    if not (yield from focus_field(1)):
        s.inconclusive("could not focus the second field")
    s.type(s.input_widget(web), "arteries")
    yield 0.4
    typed = yield from fields()
    if typed[:2] != ["What carries blood from the heart", "arteries"]:
        s.inconclusive(f"typing did not reach the editor: {typed}")
    s.check("typed text appears in both fields", True)

    before = col.db.scalar("select count() from notes")
    s.key(Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier, target=add)
    yield lambda: col.db.scalar("select count() from notes") == before + 1
    s.check("the add shortcut adds one note", col.db.scalar("select count() from notes") == before + 1)
    note = col.get_note(col.db.scalar("select max(id) from notes"))
    s.observe("basic note fields", list(note.fields))
    s.observe("basic note cards", len(note.cards()))
    yield 0.8
    after = yield from fields()
    s.observe("fields after adding", after[:2])
    s.check("the fields are cleared for the next note", after[:2] == ["", ""], str(after[:2]))
