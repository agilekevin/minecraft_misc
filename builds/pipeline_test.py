"""A deliberately unmistakable test piece.

Exists to answer one question before anything real is built on top of it: does
Litematica 1.21.8 load what litemapy writes, and does it come out the right way
round? Every block here is one whose state has not changed in many versions, so
a problem is the pipeline's rather than the palette's.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcschem import AIR, block, region, save   # noqa: E402

W = D = 11
H = 4

reg = region(W, H, D)

quartz = block("quartz_block")
dark = block("polished_blackstone")
border = block("gold_block")
marker = block("redstone_block")

for x in range(W):
    for z in range(D):
        edge = x in (0, W - 1) or z in (0, D - 1)
        reg[x, 0, z] = border if edge else (quartz if (x + z) % 2 == 0 else dark)
        for y in range(1, H):
            reg[x, y, z] = AIR

# Three-high marker at the origin corner. Orientation is the thing most likely
# to come out wrong and the hardest to notice, so it is made obvious: this
# pillar must sit at the corner with the LOWEST x and z.
for y in range(1, H):
    reg[0, y, 0] = marker

save(reg, "pipeline-test", "YeetVis Pipeline Test",
     "11x11 checkerboard, gold border, redstone pillar at the min-x/min-z corner.")
