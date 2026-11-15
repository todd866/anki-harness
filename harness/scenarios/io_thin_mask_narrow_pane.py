"""Image occlusion, upstream #3267: a mask 1% of the image wide is deleted when another mask
is moved with the note open in a narrow editor pane. In a wide window the same edit keeps it."""
from ._io_narrow_pane import run_with


def run(s):
    yield from run_with(s, thin=0.010, known="#3267")
