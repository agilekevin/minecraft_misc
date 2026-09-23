"""The STAGGERED pair, built as tested -- including the part that fails.

Two mirrored rows with NO middle wall between them, the second row raised one
block so the extended knives are diagonal neighbours rather than face
neighbours. This is here to be looked at and tweaked, not because it works.

WHAT WORKS. The knives do not interact. Measured, with a same-height control:

    same height   both extend, then NEITHER retracts -- once adjacent they
                  stick, 8 + 8 = 16 blocks, over the 12-block limit
    staggered     both extend AND both retract, every time

So the wall is not needed to keep the two knives apart. That much is real, and
it is what would save three lanes in a 5x5 -- 51x23 down to 51x20.

WHAT FAILS. The wall was doing a second job: it is the trough bank for BOTH
rows. The stagger only replaces one of them.

    lower trough   8 of 8 tiles wet -- its south bank is the UPPER ROW'S KNIFE,
                   solid, in exactly the right place, for free
    upper trough   1 of 8 tiles wet -- it drains sideways off its open north
                   side, the same failure as running with no lid at all

THE CONFLICT, precisely. The upper trough sits at y=7 in the upper plant lane.
Its north bank would have to be the block at y=7 in the LOWER plant lane -- and
that block has to stay open, because it is the shaft the lower row's own crop
falls down. One block, two incompatible jobs.

Everything else here is the shipped design: obsidian where honey must not drag,
wool knife ends, a loaded dispenser per row, one drop shaft per row.

    z=0  trench end
    z=1  row 0 firing lane        row 0 is the LOWER row, facing south
    z=2  row 0 piston lane
    z=3  row 0 rest lane (lid on top of the knife)
    z=4  row 0 PLANT              <- its trough runs at y=6
    z=5  row 1 PLANT              <- its trough runs at y=7, north side OPEN
    z=6  row 1 rest lane          row 1 is the UPPER row, facing north, +1 block
    z=7  row 1 piston lane
    z=8  row 1 firing lane
    z=9  trench end

Two levers, one per row. Two dispensers, one per row, each already holding a
water bucket. Fire a row, pulse its dispenser, and watch the upper trough empty
itself over the side.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcschem import AIR, block, container, region, save, sign  # noqa: E402

VERSION = "stagger-v0.1"


def build_region(columns=8, base_cut=5, base_top=13, nonstick="obsidian"):
    # Row 0 sits at the normal height; row 1 is lifted one block, which is the
    # whole idea -- it makes the two extended knives diagonal, not adjacent.
    ROWS = [
        dict(dy=0, backing=1, piston=2, rest=3, plant=4, facing="south"),
        dict(dy=1, plant=5, rest=6, piston=7, backing=8, facing="north"),
    ]

    W = columns + 4                      # button | cap | planted | drop | cap
    D = 10
    H = base_top + max(r["dy"] for r in ROWS) + 3
    CAP_X = 1
    LANE = range(2, columns + 2)
    DROP_X = columns + 2

    reg = region(W, H, D)

    stone = block("stone")
    soil = block("dirt")
    bamboo = block("bamboo", age="0", leaves="none", stage="0")
    bamboo_s = block("bamboo", age="0", leaves="small", stage="0")
    bamboo_l = block("bamboo", age="0", leaves="large", stage="0")
    honey = block("honey_block")
    wool = block("orange_wool")
    nostick = block(nonstick)
    hopper_d = block("hopper", facing="down", enabled="true")
    chest = block("chest", facing="north", type="single")

    for x in range(W):
        for z in range(D):
            for y in range(H):
                reg[x, y, z] = AIR
            reg[x, 0, z] = stone

    meta_rows = []
    for r in ROWS:
        dy = r["dy"]
        CUT, WATER = base_cut + dy, base_cut + 1 + dy
        SOIL, STUB, TOP = 3 + dy, 4 + dy, base_top + dy
        piston = block("sticky_piston", facing=r["facing"], extended="false")

        for x in LANE:
            # firing lane: solid through the piston's level, wire on top
            for y in range(1, CUT + 1):
                reg[x, y, r["backing"]] = stone

            # piston lane: clear at the knife's level or the knife drags it
            for y in range(1, CUT):
                reg[x, y, r["piston"]] = stone

            # rest lane: the knife parks here, with its lid on top
            for y in range(1, CUT - 1):
                reg[x, y, r["rest"]] = stone
            reg[x, CUT, r["rest"]] = (wool if x in (LANE.start, LANE.stop - 1)
                                      else honey)
            reg[x, WATER, r["rest"]] = nostick          # the lid
            for y in range(WATER + 1, TOP + 1):
                reg[x, y, r["rest"]] = stone

            # plant lane
            for y in range(1, SOIL):
                reg[x, y, r["plant"]] = stone
            reg[x, SOIL, r["plant"]] = soil
            for y in range(STUB, TOP + 1):
                reg[x, y, r["plant"]] = (bamboo_l if y == TOP else
                                         bamboo_s if y == TOP - 1 else bamboo)

        # one piston per row, bearing on the first HONEY block
        px = LANE.start + 1
        reg[px, CUT, r["piston"]] = piston
        reg[px, CUT, r["backing"]] = stone
        reg[px, CUT + 1, r["backing"]] = block(
            "lever", face="floor", facing="north", powered="false")

        # a loaded dispenser at the head of each trough
        container(reg, CAP_X, WATER, r["plant"],
                  block("dispenser", facing="east", triggered="false"),
                  [(0, "water_bucket", 1)])

        meta_rows.append(dict(r, CUT=CUT, WATER=WATER, TOP=TOP, piston_x=px))

    # ---- drop shafts: one per row, each pouring into its own hopper ---------
    for m in meta_rows:
        for y in range(1, m["TOP"] + 1):
            reg[DROP_X, y, m["plant"]] = AIR
        reg[DROP_X, 1, m["plant"]] = hopper_d
        reg[DROP_X, 0, m["plant"]] = chest
    for z in range(D):
        if z not in (ROWS[0]["plant"], ROWS[1]["plant"]):
            for y in range(1, max(m["TOP"] for m in meta_rows) + 1):
                reg[DROP_X, y, z] = stone
        # the knife must not drag the shaft wall
    for m in meta_rows:
        reg[DROP_X, m["CUT"], m["rest"]] = stone      # wool end, so stone is fine

    # ---- end caps ----------------------------------------------------------
    top_all = max(m["TOP"] for m in meta_rows)
    for x in (CAP_X, W - 1):
        for z in range(D):
            for y in range(1, top_all + 1):
                if reg[x, y, z].id.endswith("dispenser"):
                    continue
                reg[x, y, z] = stone
    for m in meta_rows:
        container(reg, CAP_X, m["WATER"], m["plant"],
                  block("dispenser", facing="east", triggered="false"),
                  [(0, "water_bucket", 1)])
        reg[CAP_X - 1, m["WATER"], m["plant"]] = block(
            "stone_button", face="wall", facing="west", powered="false")

    # ---- signs, because the failure is invisible until you run it ----------
    lower, upper = meta_rows
    sign(reg, LANE.start, top_all + 1, ROWS[0]["plant"],
         ["LOWER TROUGH", "8 of 8 wet", "bank = upper", "row's knife"])
    sign(reg, LANE.start, top_all + 1, ROWS[1]["plant"],
         ["UPPER TROUGH", "1 of 8 wet", "no north bank", "-- drains out"])
    sign(reg, LANE.start + 3, top_all + 1, 0,
         ["Stagger test", VERSION, "knives OK", "troughs not"])

    meta = dict(W=W, H=H, D=D, CAP_X=CAP_X, LANE=LANE, DROP_X=DROP_X,
                rows=meta_rows, columns=columns)
    return reg, meta


reg, META = build_region()

if __name__ == "__main__":
    save(reg, "bamboo-stagger", f"Bamboo Stagger {VERSION}",
         "Two mirrored rows, no middle wall, upper row raised one block. "
         "The knives work; the upper trough has no north bank and drains.")
