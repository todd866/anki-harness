"""Cloze: the same awkward cloze texts rendered on every version.

No expected output is written down. For each text the scenario records how many cards it
makes and what each card's question and answer render to; the runner reports any that differ
between versions. The corpus leans on MathJax and nested or malformed braces, because 26.11
changes how a cloze is closed inside MathJax (#4612).
"""
import re

TEXTS = [
    "{{c1::plain}}",
    "{{c1::answer::hint}}",
    "{{c1::a}} and {{c1::b}} on one card",
    "{{c1::first}} {{c2::second}} {{c3::third}}",
    "{{c2::only a second ordinal}}",
    "{{c10::ten}} then {{c1::one}}",
    "{{c1::outer {{c2::inner}} outer}}",
    "{{c1::{{c1::same ordinal nested}}}}",
    "{{c1,2::shared by two cards}} and {{c3::alone}}",
    "{{c1::}}",
    "{{c1::answer::}}",
    "{{c1::a::b::c}}",
    "{{c0::zero}}",
    "{{C1::upper case c}}",
    "{{c1:single colon}}",
    "{{c1::extra brace}}}",
    "stray }} before {{c1::a}}",
    "{{c1::unclosed",
    "{{c1::<b>bold</b> and <i>italic</i>}}",
    "<div>{{c1::inside a div}}</div><div>second line</div>",
    "{{c1::line one<br>line two}}",
    "{{c1::a&nbsp;b &lt; c}}",
    '{{c1::<img src="x.png">}}',
    r"\(x = {{c1::y}}\)",
    r"\( {{c1::\frac{a}{b}}} \)",
    r"{{c1::\(\frac{a}{b}\)}}",
    r"{{c1::\(a_{{b}}\)}} after",
    r"\(x_{ {{c1::i}} }\) and \(y^{ {{c2::j}} }\)",
    r"{{c1::\(\frac{1}{{2}}\)}} and {{c2::plain}}",
    r"\[ {{c1::\sum_{i=1}^{n} i}} = {{c2::\frac{n(n+1)}{2}}} \]",
    r"\(\text{rate} = {{c1::k[A]^{2}}}\) with {{c1::second order::order}}",
    r"{{c1::\(e^{-x}}\)}}",
    r"\( {{c1::a}} \) {{c2::b}} \( {{c3::c}} \)",
    r"{{c1::\[ \begin{matrix} a & b \\ c & d \end{matrix} \]}}",
    "[$]{{c1::\\alpha}}[/$] and [$$]{{c2::\\beta}}[/$$]",
    "{{c1::a}}{{c2::b}}{{c1::c}}{{c2::d}}",
    "Dose {{c1::5 mg/kg}} every {{c2::8 h::interval}} for {{c3::7 days}}",
    "{{c1::a | b}} {{c2::c::d | e}}",
    "{{c1::ends with colon:}} {{c2:::starts with colon}}",
    "{{c1::emoji 🧠 and accents é ü}}",
]

STYLE = re.compile(r"<style>.*?</style>", re.S)
DOCS_LINK = re.compile(r"https://docs\.ankiweb\.net/[^'\"]*")  # the manual's addresses moved between versions


def clean(html: str) -> str:
    return re.sub(r"\s+", " ", DOCS_LINK.sub("https://docs.ankiweb.net/…", STYLE.sub("", html))).strip()


def run(s):
    col = s.col
    notetype = next(m for m in col.models.all() if m["type"] == 1)
    deck = col.decks.id("harness")
    for index, text in enumerate(TEXTS):
        label = f"{index:02d} {text[:48]}"
        try:
            note = col.new_note(notetype)
            note.fields[0] = text
            col.add_note(note, deck)
            cards = sorted(note.cards(), key=lambda c: c.ord)
            s.observe(f"{label} | cards", [c.ord + 1 for c in cards])
            for card in cards:
                s.observe(f"{label} | card {card.ord + 1} question", clean(card.question()))
                s.observe(f"{label} | card {card.ord + 1} answer", clean(card.answer()))
        except Exception as error:
            s.observe(f"{label} | cards", f"error ({type(error).__name__})")
    yield 0.1
    s.check("a plain cloze makes one card", s.observations.get(f"00 {TEXTS[0][:48]} | cards") == [1])
