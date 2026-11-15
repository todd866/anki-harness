"""Search: the same searches over the same small collection, on every version.

No expected answers are written down. Each search's result count is recorded, and the runner
reports any search whose count differs between versions. Searches that hold a comparator
followed by a number are here because 26.11 gives them a new meaning (numeric field
comparison), which changes what plain text searches such as `p=0.05` find.
"""

NOTES = [
    "The difference was significant at p=0.05 in the trial.",
    "Replace potassium if K=3.5 or lower.",
    "Arterial pH=7.4 is normal.",
    "An n=1 study.",
    "E=mc2 relates mass and energy.",
    "Let x=5 and y=10.",
    "CD4<200 needs prophylaxis.",          # as typed through the API
    "CD4&lt;200 needs prophylaxis.",       # as the editor stores it
    "Obesity is BMI&gt;30.",
    "Dose 1-5 mg, range 3..7.",
    "Plain text with no numbers at all.",
    "<b>Bold</b> answer a=b here.",
]
FREQUENCY = [("alpha", "100"), ("beta", "500"), ("gamma", "1000"), ("delta", "abc"), ("epsilon", " 42 ")]

SEARCHES = [
    "p=0.05", '"p=0.05"', "K=3.5", "pH=7.4", "n=1", "x=5", '"x=5 and"', "x=5*", "*=5*", "E=mc2", "a=b",
    "CD4<200", '"CD4<200"', "CD4&lt;200", "BMI>30", "BMI&gt;30",
    r"x\=5", r"p\=0.05",
    "front:*p=0.05*", "re:x=5", "nc:pH=7.4",
    "Frequency>500", "frequency>=500", "Frequency=100", "Frequency<50", "Frequency=42",
    "1-5", "=5", "<b>", "3..7",
    "prop:ivl>=0", "prop:due<=1", "prop:reps=0", "is:new", "deck:harness", "tag:t1", "-tag:t1", "added:1",
    "significant", "significant trial", "significant or potassium", "-significant", "plain text",
]


def run(s):
    col = s.col
    basic = col.models.by_name("Basic")
    deck = col.decks.id("harness")
    for i, text in enumerate(NOTES):
        note = col.new_note(basic)
        note["Front"] = text
        note["Back"] = f"back {i}"
        note.tags = ["t1"] if i % 2 == 0 else ["t2"]
        col.add_note(note, deck)
    # A note type with a field named Frequency, for the comparisons the new syntax is meant for.
    freq = col.models.new("Vocab")
    for name in ("Word", "Frequency"):
        col.models.add_field(freq, col.models.new_field(name))
    template = col.models.new_template("Card 1")
    template["qfmt"], template["afmt"] = "{{Word}}", "{{Frequency}}"
    col.models.add_template(freq, template)
    col.models.add(freq)
    freq = col.models.by_name("Vocab")
    for word, value in FREQUENCY:
        note = col.new_note(freq)
        note["Word"], note["Frequency"] = word, value
        col.add_note(note, deck)
    yield 0.1
    s.observe("notes in the collection", col.db.scalar("select count() from notes"))
    for search in SEARCHES:
        try:
            result = len(col.find_notes(search))
        except Exception as error:
            result = f"error ({type(error).__name__})"
        s.observe(f"search  {search}", result)
    s.check("a plain word search finds its note", len(col.find_notes("significant")) == 1)
