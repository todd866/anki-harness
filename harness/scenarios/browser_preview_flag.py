"""Browser preview: does it redraw when the card's flag or deck changes?

Upstream #4832: a card template that shows {{CardFlag}} or {{Deck}} keeps showing the old
value in the browser's preview after the card is flagged or moved, because the preview only
redraws when the note's text changes. The control is a change to the note's text, which the
preview does pick up.
"""
import aqt


def run(s):
    col = s.col
    basic = col.models.by_name("Basic")
    template = basic["tmpls"][0]
    template["qfmt"] = "<div id=probe>{{Front}} | flag:{{CardFlag}} | deck:{{Deck}}</div>"
    col.models.update_dict(basic)
    first = col.decks.id("harness")
    second = col.decks.id("elsewhere")
    note = col.new_note(basic)
    note["Front"], note["Back"] = "preview me", "back"
    col.add_note(note, first)
    card_id = note.cards()[0].id

    browser = aqt.dialogs.open("Browser", s.mw)
    yield 0.8
    browser.search_for(f"cid:{card_id}")
    yield 0.6
    browser.table.select_single_card(card_id)
    yield 0.4
    browser.onTogglePreview()
    yield 1.0
    previewer = browser._previewer
    if previewer is None or previewer._web is None:
        s.inconclusive("the preview window did not open")

    def shown():
        for _ in range(40):
            s.js(previewer._web, "(document.getElementById('probe') || {}).innerText || ''", "probe")
            yield s.have("probe")
            if s.scratch["probe"].strip():
                return s.scratch["probe"].strip()
            yield 0.2
        return ""

    start = yield from shown()
    s.observe("preview at start", start)
    if "preview me" not in start:
        s.inconclusive(f"the preview did not draw the card: {start!r}")

    # Control: change the note's text.
    edited = col.get_note(note.id)
    edited["Front"] = "preview me again"
    aqt.operations.note.update_note(parent=browser, note=edited).run_in_background()
    yield 1.5
    after_text = yield from shown()
    s.observe("preview after a text change", after_text)
    if "preview me again" not in after_text:
        s.inconclusive(f"the preview did not follow a text change either: {after_text!r}")
    s.check("control: the preview follows a change to the note's text", True)

    browser.set_flag_of_selected_cards(1)
    yield lambda: col.get_card(card_id).user_flag() == 1
    yield 1.5
    after_flag = yield from shown()
    s.observe("preview after flagging", after_flag)
    s.check("the preview shows the new flag", "flag:flag1" in after_flag, f"the card is flagged red and the preview still shows: {after_flag}", known="#4832")

    aqt.operations.card.set_card_deck(parent=browser, card_ids=[card_id], deck_id=second).run_in_background()
    yield lambda: col.get_card(card_id).did == second
    yield 1.5
    after_move = yield from shown()
    s.observe("preview after moving deck", after_move)
    s.check("the preview shows the new deck", "deck:elsewhere" in after_move, f"the card is in 'elsewhere' and the preview still shows: {after_move}", known="#4832")
