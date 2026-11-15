"""Browser: search, select, narrow the search, widen it again, flag the selection.

26.11 reworks how the browser restores a selection after a search and how it reads the
selected rows' flags (#5755, #5756, #5768, all for speed on large selections). This walks the
same steps on every version and records the counts, so a change in what stays selected would
show as a difference.
"""
import aqt

NOTES = 60


def run(s):
    col = s.col
    basic = col.models.by_name("Basic")
    deck = col.decks.id("harness")
    for i in range(NOTES):
        note = col.new_note(basic)
        note["Front"] = f"item {i:02d} {'even' if i % 2 == 0 else 'odd'} {'third' if i % 3 == 0 else 'other'}"
        note["Back"] = f"back {i:02d}"
        col.add_note(note, deck)
    browser = aqt.dialogs.open("Browser", s.mw)
    table = browser.table
    yield 0.8

    def search(text):
        browser.search_for(text)
        yield 0.6

    def counts(label):
        s.observe(f"{label}: rows", table.len())
        s.observe(f"{label}: selected", table.len_selection(refresh=True))

    yield from search("deck:harness")
    counts("all cards")
    s.check("the search shows every card", table.len() == NOTES, str(table.len()))

    table.select_all()
    yield 0.4
    counts("after select all")
    s.check("select all selects every row", table.len_selection(refresh=True) == NOTES, str(table.len_selection()))

    yield from search("deck:harness even")
    counts("narrowed to even")
    s.observe("narrowed: selected fronts", sorted(col.get_card(c).note()["Front"][:7] for c in table.get_selected_card_ids())[:5])

    yield from search("deck:harness")
    counts("widened again")

    table.clear_selection()
    yield 0.2
    yield from search("deck:harness third")
    table.select_all()
    yield 0.3
    counts("thirds selected")
    browser.set_flag_of_selected_cards(2)
    yield lambda: col.db.scalar("select count() from cards where flags = 2") > 0
    yield 0.4
    s.observe("cards flagged", col.db.scalar("select count() from cards where flags = 2"))
    s.check("flagging the selection flags exactly the selected cards", col.db.scalar("select count() from cards where flags = 2") == NOTES // 3, str(col.db.scalar("select count() from cards where flags = 2")))
    s.observe("undo label after flagging", s.undo_label())

    yield from search("deck:harness flag:2")
    counts("search by the new flag")
    yield from search("deck:harness")
    counts("everything again")
    table.invert_selection()
    yield 0.3
    counts("after invert selection")
