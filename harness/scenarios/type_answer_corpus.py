"""Type-in-the-answer: the same expected and typed pairs compared on every version.

No expected output is written down; the comparison HTML for each pair is recorded and the
runner reports any that differ. 26.11 reworks this code to add a case-insensitive modifier
(#5264), so the ordinary case-sensitive comparison is what is being watched here.
"""
import re

PAIRS = [
    ("aorta", "aorta"),
    ("aorta", "Aorta"),
    ("Aorta", "aorta"),
    ("aorta", "aorte"),
    ("aorta", ""),
    ("", "aorta"),
    ("left ventricle", "left  ventricle"),
    ("left ventricle", " left ventricle "),
    ("left ventricle", "leftventricle"),
    ("naïve", "naive"),
    ("naive", "naïve"),
    ("café", "café"),
    ("Ångström", "Angstrom"),
    ("ß", "ss"),
    ("İstanbul", "istanbul"),
    ("5 mg/kg", "5mg/kg"),
    ("5 mg/kg", "5 mg / kg"),
    ("1,000", "1000"),
    ("pH 7.35–7.45", "pH 7.35-7.45"),
    ("<b>bold</b>", "bold"),
    ("a &amp; b", "a & b"),
    ("a<br>b", "a b"),
    ("日本語", "日本"),
    ("مرحبا", "مرحب"),
    ("🧠 brain", "brain"),
    ("answer", "ANSWER"),
    ("The quick brown fox", "The quick brown dog"),
    ("x" * 60, "x" * 59 + "y"),
    ("tab\tseparated", "tab separated"),
    ("line\nbreak", "line break"),
]


def clean(html: str) -> str:
    return re.sub(r"\s+", " ", html).strip()


def run(s):
    col = s.col
    for index, (expected, typed) in enumerate(PAIRS):
        label = f"{index:02d} expected {expected[:24]!r} typed {typed[:24]!r}"
        try:
            s.observe(label, clean(col.compare_answer(expected, typed)))
        except Exception as error:
            s.observe(label, f"error ({type(error).__name__})")
    yield 0.1
    same = s.observations[f"00 expected {'aorta'!r} typed {'aorta'!r}"]
    s.check("an exact answer is marked correct with nothing marked wrong", "typeGood" in same and "typeBad" not in same and "typeMissed" not in same, same)
