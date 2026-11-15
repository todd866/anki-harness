"""Tags: does a saved expansion survive a rename, and an undo and redo of note creation?

Upstream #5967 (renaming a tag subtree collapses it) and #5966 (redoing note creation
restores the tag as it was when first added, losing an expansion saved since). Large tag
trees are how big shared decks are organised, so a tree that keeps collapsing is felt daily.
The control is the plain case: an expanded tag stays expanded when nothing else happens.
"""


def expanded(col, name: str):
    """True or False for a tag's expansion in the tree, None if the tag is not there."""
    node = col.tags.tree()
    for part in name.split("::"):
        node = next((child for child in node.children if child.name == part), None)
        if node is None:
            return None
    return not node.collapsed


def run(s):
    col = s.col
    s.add_cloze("harness", ["One: {{c1::a}}."], tags=["alpha::beta::gamma"])
    col.tags.set_collapsed("alpha", collapsed=False)
    col.tags.set_collapsed("alpha::beta", collapsed=False)
    yield 0.1
    s.observe("expanded before", [expanded(col, "alpha"), expanded(col, "alpha::beta")])
    if expanded(col, "alpha") is not True or expanded(col, "alpha::beta") is not True:
        s.inconclusive("could not expand the tags to begin with")
    s.check("control: an expanded tag stays expanded", True)

    col.tags.rename("alpha", "omega")
    yield 0.1
    after_rename = [expanded(col, "omega"), expanded(col, "omega::beta")]
    s.observe("expanded after renaming the parent", after_rename)
    s.check("a renamed tag subtree keeps its expansion", after_rename == [True, True], f"alpha and alpha::beta were expanded; after renaming alpha to omega: {after_rename}", known="#5967")

    # Redo of note creation. The note carries the parent tag itself as well as the child, so
    # the parent's row is created by the note and belongs to its undo entry.
    s.add_cloze("harness", ["Two: {{c1::b}}."], tags=["delta", "delta::epsilon"])
    col.tags.set_collapsed("delta", collapsed=False)
    yield 0.1
    if expanded(col, "delta") is not True:
        s.inconclusive("could not expand the second tag")
    col.undo()
    col.redo()
    yield 0.1
    s.observe("expanded after undo and redo of the note", expanded(col, "delta"))
    s.check("a tag expansion survives undo and redo of the note that introduced it", expanded(col, "delta") is True, f"delta was expanded; after undo and redo it is {'expanded' if expanded(col, 'delta') else 'collapsed or missing'}", known="#5966")
