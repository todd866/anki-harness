"""Image occlusion: a mask 1.5% of the image wide, edited in a narrow editor pane.

Same steps as io_thin_mask_narrow_pane with a larger mask. Whether it survives depends on how
large the editor draws the image in a narrow pane, so this one separates versions that lay
the mask editor out differently."""
from ._io_narrow_pane import run_with


def run(s):
    yield from run_with(s, thin=0.015)
