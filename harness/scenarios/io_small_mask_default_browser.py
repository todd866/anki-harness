"""Image occlusion: a mask 1.5% of the image wide, edited with the browser at its default size.

Same steps as io_thin_mask_default_browser with a larger mask. Whether it survives depends on how
large the editor draws the image in the pane, so this one separates versions that lay the
mask editor out differently."""
from ._io_small_masks import run_with


def run(s):
    yield from run_with(s, thin=0.015)
