"""Bamboo harvester test rig — one sticky piston, a honey row, 12 columns.

A sticky piston pushes a 1x12 row of honey blocks sideways into the bamboo.
Honey blocks drag their neighbours, so pushing the one block in front of the
piston moves the whole row, and every stalk it moves into is destroyed —
bamboo is destroy-on-push. Twelve columns harvested by one piston.

Twelve is not an arbitrary lane length: a piston moves at most 12 blocks, and
the honey row is exactly 12. That leaves ZERO margin, which is the main
fragility here. Honey sticks to everything it touches, so anything adjacent to
the row gets added to the push, the total goes to 13, and the piston silently
does nothing at all. Hence the air gaps above, below and behind the row — they
are structural, not decoration.

Still measuring the same thing: what fraction of the crop is recoverable. The
only solid block at planting level is the 1x1 soil pillar, so an item has to
land on exactly that to be stranded; everything else falls into a hopper gap.

Still deliberately not the real farm: a lever fires it rather than observers,
and hoppers collect rather than water, so the experiment measures capture and
nothing else.

Cross-section, looking along the lane (+z is south):

    z=0   backing block + lever (x=0 only)
    z=1   sticky piston at y=6 (x=0 only) - MUST be air elsewhere at y=6
    z=2   honey row at y=6, hopper gap at y=2
    z=3   PLANT - soil at y=3, bamboo from y=4
    z=4   hopper gap at y=2
    z=5   wall

The push destroys the segment at y=6, so y=4 and y=5 survive and regrow. At
Eden's max of 10 the plant fills y=4..13, so a harvest drops eight per column.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcschem import AIR, block, region, save   # noqa: E402

COLUMNS = 12       # exactly the piston push limit; see module docstring
CUT_Y = 6
TOP_Y = 13

W, H, D = COLUMNS, TOP_Y + 1, 6

reg = region(W, H, D)

stone = block("stone")
soil = block("dirt")
bamboo = block("bamboo", age="0", leaves="none", stage="0")
bamboo_small = block("bamboo", age="0", leaves="small", stage="0")
bamboo_large = block("bamboo", age="0", leaves="large", stage="0")
honey = block("honey_block")
sticky = block("sticky_piston", facing="south", extended="false")
hopper_w = block("hopper", facing="west", enabled="true")
hopper_d = block("hopper", facing="down", enabled="true")
chest = block("chest", facing="north", type="single")
lever = block("lever", face="floor", facing="north", powered="false")

for x in range(W):
    for z in range(D):
        for y in range(H):
            reg[x, y, z] = AIR

    # --- floor -------------------------------------------------------------
    for z in range(D):
        reg[x, 0, z] = stone
        reg[x, 1, z] = stone

    # --- collection: a hopper gap either side of the plant, chaining west ---
    for z in (2, 4):
        reg[x, 2, z] = hopper_w if x > 0 else hopper_d

    # --- planting column ---------------------------------------------------
    # The only solid block at this level, so it is the only place a drop can
    # strand. That is the measurement.
    reg[x, 2, 3] = stone
    reg[x, 3, 3] = soil
    # Pre-grown to Eden's max of 10 segments (y=4..13) so the rig can be
    # fired immediately instead of waiting for growth. Leaves on the top two,
    # as bamboo generates.
    for y in range(4, TOP_Y + 1):
        if y == TOP_Y:
            reg[x, y, 3] = bamboo_large
        elif y == TOP_Y - 1:
            reg[x, y, 3] = bamboo_small
        else:
            reg[x, y, 3] = bamboo

    # --- the honey row -----------------------------------------------------
    # y=5, y=7 and z=1 are left as air on purpose. Honey drags whatever touches
    # it, and one extra block takes the push from 12 to 13, at which point the
    # piston does nothing and gives no indication why.
    reg[x, CUT_Y, 2] = honey

    # --- retaining wall, kept well clear of the honey ----------------------
    for y in range(2, 4):
        reg[x, y, 5] = stone

# --- the single piston, at the west end ------------------------------------
reg[0, CUT_Y, 1] = sticky
reg[0, CUT_Y, 0] = stone            # not adjacent to the honey at z=2
reg[0, CUT_Y + 1, 0] = lever

# Chests under the end of each hopper chain.
for z in (2, 4):
    reg[0, 1, z] = chest

save(reg, "bamboo-harvest-test", "Bamboo Harvest Test Rig",
     f"{COLUMNS} columns, one sticky piston pushing a {COLUMNS}-honey row at "
     f"y={CUT_Y}. Hopper gaps both sides, lever-fired. Bamboo pre-grown to 10.")
