"""Media: the same sequence of files added on every version, and the names Anki gives them.

No expected output is written down. Adding a file whose name already exists (same content,
different content, different letter case, different Unicode form) is where naming rules
matter, and 26.11 changes one of them (#5683: use the existing file's own name when adding).
"""

STEPS = [
    ("image.png", b"one"),
    ("image.png", b"one"),            # same name, same content
    ("image.png", b"two"),            # same name, different content
    ("Image.png", b"one"),            # different case, same content as the first
    ("IMAGE.PNG", b"three"),          # different case, new content
    ("café.png", b"four"),            # composed
    ("café.png", b"four"),      # decomposed, same content
    ("café.png", b"five"),      # decomposed, new content
    ("a b.png", b"six"),
    ("a  b.png", b"six"),
    ("a/b.png", b"seven"),
    ("a:b?.png", b"eight"),
    (".hidden.png", b"nine"),
    ("trailing.png ", b"ten"),
    ("noextension", b"eleven"),
    ("x" * 150 + ".png", b"twelve"),
    ("image.png", b"one"),            # the first file again, at the end
]


def run(s):
    media = s.col.media
    for index, (name, data) in enumerate(STEPS):
        label = f"{index:02d} add {name[:28]!r} ({data.decode()})"
        try:
            s.observe(label, media.write_data(name, data))
        except Exception as error:
            s.observe(label, f"error ({type(error).__name__})")
    yield 0.1
    import os

    s.observe("files on disk", sorted(os.listdir(media.dir())))
    s.check("adding the same file twice gives the same name", s.observations["00 add 'image.png' (one)"] == s.observations["01 add 'image.png' (one)"])
