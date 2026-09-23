"""The receptacle at the end of a bamboo water stream, for Eden.

WHAT THE MEASUREMENTS FORCED

The first draft of this file was a hopper bank: the last several tiles of the
stream floored with hoppers, on the theory that items wash over them and a full
hopper simply passes the rest downstream. exp30 killed it. Four hoppers under a
flowing stream split a 2048-item burst

    [64, 64, 64, 505]

and eight hoppers split it [512, 0, 0, 0, 0, 0, 0, 0] -- banking 506 where a
single hopper banked 504. Items settle into the first hopper's bowl and the
current pins the rest against the far wall; a hopper bank under a current is
decoration. Hoppers only count toward capacity if each has its OWN drop point.

So a collection point is one shaft over one hopper, which exp27 measured at
99.3% delivery, and the way to scale is to build more of them rather than to
make one bigger.

CAPACITY, per collection point:

    5 slots * 64 buffered  +  2.5 items/s * 300 s despawn  ~= 1070 bamboo
    at 9 bamboo per Eden plant (capped at 10, broken 1 above the dirt)
        -> about 118 plants harvested SIMULTANEOUSLY per hopper

That ceiling is set by the despawn clock, so it does not move when
RealisticBiomes slows the growth rate -- slower growth buys throughput, never
burst headroom. Stagger the harvest and the binding limit becomes the average
instead, which is 9000 bamboo/hour per hopper.

Eden allows 16 hoppers per chunk, so a chunk holds at most 16 collection
points. Citadel reinforces obsidian, hoppers and barrels but NOT bamboo or
pistons, so this -- the part holding the loot -- is the part worth diamond.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mcschem                                                 # noqa: E402
from mcschem import block                                      # noqa: E402

CHANNEL = 6            # channel tiles; a water source spreads 7, so one is enough

OBS = block("obsidian")
HOPPER_DOWN = block("hopper", facing="down", enabled="true")
BARREL = block("barrel", facing="up", open="false")
WATER = block("water", level="0")
AIR = mcschem.AIR

# No drop shaft: the LAST FLOOR TILE of the channel is the hopper, with the end
# wall right behind it. exp30 measured exactly this shape banking 505 of a 2048
# burst -- the full single-hopper capacity -- because the current pins the crop
# against the wall and holds it on that hopper. A shaft would work equally well
# (exp31: 503) but the channel's water pours down it into the chamber, which is
# extra structure for no extra crop.
#
#   x=0            inlet, open, where the existing stream is joined
#   x=1            water source
#   x=2..CHANNEL   channel floor
#   x=CHANNEL+1    THE HOPPER -- the floor tile the crop piles onto
#   x=CHANNEL+2    end wall
WIDTH = CHANNEL + 3
HEIGHT = 4             # 0 storage, 1 floor/hopper, 2 channel, 3 lid
DEPTH = 3

Y_STORE, Y_FLOOR, Y_CHAN, Y_LID = 0, 1, 2, 3
Z_CH = 1
HOPPER_X = CHANNEL + 1


def build():
    reg = mcschem.region(WIDTH, HEIGHT, DEPTH)
    for x in range(WIDTH):
        for z in range(DEPTH):
            if z != Z_CH or x == WIDTH - 1:      # banks, and the end wall
                for y in range(HEIGHT):
                    reg[x, y, z] = OBS
                continue

            reg[x, Y_LID, z] = OBS
            reg[x, Y_CHAN, z] = WATER if x >= 1 else AIR
            if x == HOPPER_X:
                reg[x, Y_FLOOR, z] = HOPPER_DOWN
                reg[x, Y_STORE, z] = BARREL
            else:
                reg[x, Y_FLOOR, z] = OBS
                reg[x, Y_STORE, z] = OBS

    reg[0, Y_CHAN, Z_CH] = AIR                   # inlet stays open
    reg[0, Y_LID, Z_CH] = AIR
    return reg


if __name__ == "__main__":
    reg = build()
    cap = 5 * 64 + 2.5 * 300
    print(f"module {WIDTH} x {HEIGHT} x {DEPTH}, hopper at x={HOPPER_X}")
    print(f"capacity  ~{cap:.0f} bamboo per harvest = {cap/9:.0f} plants at once")
    print(f"storage    1728 bamboo (barrel); a double chest below gives 3456")
    print(f"Eden       16 of these per chunk, max")
    path = mcschem.save(
        reg, "bamboo_receptacle",
        name="Bamboo receptacle (one collection point)",
        description="Stream -> terminal hopper -> barrel. ~1070 bamboo per "
                    "harvest burst = ~118 plants. Replicate it; do NOT merge "
                    "streams onto one hopper (exp30).")
    print("saved:", path)
