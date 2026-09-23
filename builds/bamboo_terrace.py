"""Terraced bamboo harvester -- no middle walls, no slime, one shaft per tier.

Everything here is a consequence of something measured on the rig. The design
notes below say which.

WHY TERRACE AT ALL. Two mirrored rows driving their knives toward each other end
up face-adjacent, and two honey rows in contact are 16 blocks -- over the piston
limit. Measured: at the same height both extend and then NEITHER retracts. Lift
one row a block and the extended knives become diagonal neighbours, which is not
adjacency for stickiness: both extend and both retract, every time. That is what
lets the wall between them go, and the wall is a lane per pair.

THE HEIGHTS ALTERNATE IN PAIRS, they do not climb: 0, 1, 1, 0, 0, 1, 1, ...
Two constraints pull against each other. Inside a pair the tiers must differ by
one block or their knives lock together. Across a pair boundary they SHARE a
backing column to save a lane, and one column carries one firing line, so those
two must sit at the same height. Alternating ascending and descending pairs
satisfies both, and a tall grid stays two blocks tall rather than climbing.

WHAT EACH TROUGH IS BOUNDED BY -- this is the whole trick:

    the LOWER tier of a pair   one bank is THE HIGHER TIER'S KNIFE, free
    the HIGHER tier of a pair  one bank is THE BLOCKING BLADE

The lower tier's bank costs nothing: its partner is one block up and one lane
over, so that partner's extended knife lands exactly where the bank belongs.

The higher tier's bank is the hard one. It would have to occupy the block the
tier below drops its crop through -- solid for the water, open for the crop, same
block. A BLOCKING BLADE resolves it: a second honey row in the lower tier's
stack, fired AFTER the cut, which arrives at that block once the crop has already
fallen past. Measured: it moves 8/8 and retracts 8/8, and it takes the upper
trough from 1 of 8 tiles wet to 8 of 8.

WHY EACH TIER KEEPS ITS OWN SHAFT. Letting an upper tier wash its crop down into
the one below looks elegant and does not work. Measured over three runs each:

    shaft per tier   2 tiers 99.3%, 3 tiers 144/144 twice, 4 tiers 99.8%
    cascading down   2 tiers 6.2%; 3 tiers 138, 35, 84 of 144

The cascade is not merely worse, it is erratic -- a fourfold swing on identical
geometry. Unpredictable is worse than mediocre, because you cannot tell a broken
machine from a bad day.

NO SLIME ANYWHERE. Honey drags whatever it touches, so the blocks that must touch
it and stay put used to be slime. Two measured replacements: wool for the knife's
END blocks, because a dragged plain block does not grip its own neighbours; and
obsidian everywhere else, because honey cannot move an immovable block and --
this is the part that matters -- the piston fires anyway rather than jamming.

BLADES CHAIN. Wool ends make each 8-column blade its own push set: firing one
segment moves 8/8 of it and 0/8 of its neighbour. Segments can sit end to end for
as far as you like. They still need a drop every 8 columns, because one water
source reaches exactly 8 tiles and a trough only sweeps when its single escape is
at the far end -- so the module pitch stays 10. The chaining matters if you ever
want a blade longer than its trough.

THE SEQUENCE, five steps now rather than four:

    1. lever A   cutting knives extend; crop falls onto them
    2. lever B   blocking blades extend, closing the odd tiers' troughs
    3. button    dispensers place a source at each trough head
    4. button    the same dispensers take the water back -- THIS IS LIFE
                 SUPPORT: a column left flooded keeps its stub and never grows
                 again, and nothing in the physics stops you retracting early
    5. levers    everything retracts

WHAT IS NOT WIRED. The dispensers are placed and loaded but have no bus: the
tiers sit at two different heights, so the single-level bus the flat grid uses
does not reach them. Each tier's dispensers are reachable from its own cap face.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcschem import AIR, block, container, region, save, sign  # noqa: E402

VERSION = "terrace-v0.3"


def height_of(r):
    """Which of the two levels tier r sits on: 0, 1, 1, 0, 0, 1, 1, ...

    Two constraints pull against each other and this pattern satisfies both.
    WITHIN a pair the two tiers must differ by one block, or their knives end up
    face-adjacent and neither can retract. ACROSS a pair boundary the two tiers
    share a backing column to save a lane -- and a shared column carries exactly
    one firing line, so those two tiers must sit at the SAME height. Alternating
    the pairs ascending / descending gives every tier a partner one block off
    inside its pair, and a neighbour at its own level across the boundary.
    """
    return 0 if r % 4 in (0, 3) else 1


def tier_layout(r):
    """Lanes, facing and height for tier r.

    Pairs share a backing column, so the period is 7 lanes per two tiers rather
    than 8. The two tiers of a pair face each other with their plant lanes
    adjacent and NO WALL between them -- the higher one's knife is the lower
    one's trough bank, which is the whole point of terracing.
    """
    base = 1 + (r // 2) * 7
    dy = height_of(r)
    if r % 2 == 0:
        return dict(backing=base, piston=base + 1, rest=base + 2,
                    plant=base + 3, facing="south", dy=dy)
    return dict(plant=base + 4, rest=base + 5, piston=base + 6,
                backing=base + 7, facing="north", dy=dy)


def build_region(tiers=4, cols=3, columns=8, cut_y=5, top_y=13,
                 knife_ends="wool", nonstick="obsidian", add_sign=True):
    X_PITCH = columns + 2                       # cap | planted | drop shaft
    W = cols * X_PITCH + 1
    CAP_X = 0
    LOW_CUT = cut_y

    lay = [tier_layout(r) for r in range(tiers)]
    D = max(max(l["backing"], l["plant"]) for l in lay) + 2
    # A blocking blade rides two levels above its own tier's knife, which puts
    # it exactly at the trough level of the tier one block higher.
    BLOCK_Y = LOW_CUT + 2
    CONTAIN_Y = top_y + 1
    H = CONTAIN_Y + 2

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
    dust = block("redstone_wire", east="side", west="side",
                 north="side", south="side", power="0")
    lever = block("lever", face="floor", facing="north", powered="false")
    # facing names a repeater's INPUT side, so a line running east faces west
    repeater = block("repeater", facing="west", delay="1",
                     locked="false", powered="false")

    for x in range(W):
        for z in range(D):
            for y in range(H):
                reg[x, y, z] = AIR
            reg[x, 0, z] = stone

    caps = [m * X_PITCH for m in range(cols)] + [cols * X_PITCH]
    drops = [m * X_PITCH + columns + 1 for m in range(cols)]
    meta_tiers = []

    for r, L in enumerate(lay):
        CUT = LOW_CUT + L["dy"]
        TROUGH = CUT + 1
        SOIL, STUB, TOP = 3 + L["dy"], 4 + L["dy"], top_y + L["dy"]
        piston = block("sticky_piston", facing=L["facing"], extended="false")
        # The blocking blade lives in whichever tier of the pair sits LOWER,
        # and reaches the block the HIGHER tier's trough needs for its north
        # bank -- the one block that must be open while crop falls and solid
        # while water runs. Which tier that is flips with the pair's direction.
        pair_first = (r // 2) * 2
        pair = [t for t in (pair_first, pair_first + 1) if t < tiers]
        wants_blocker = (len(pair) == 2
                         and r == min(pair, key=height_of)
                         and height_of(pair[0]) != height_of(pair[1]))

        for m in range(cols):
            first = m * X_PITCH + 1
            lane = range(first, first + columns)

            for x in lane:
                # backing: solid through the knife's level, wire on top
                for y in range(1, CUT + 1):
                    reg[x, y, L["backing"]] = stone

                # piston lane: clear at the knife's level or the knife drags it
                for y in range(1, CUT):
                    reg[x, y, L["piston"]] = stone

                # rest lane: the knife parks, its lid sits on top
                for y in range(1, CUT - 1):
                    reg[x, y, L["rest"]] = stone
                end = x in (first, first + columns - 1)
                reg[x, CUT, L["rest"]] = (wool if knife_ends == "wool" and end
                                          else honey)
                reg[x, TROUGH, L["rest"]] = nostick           # the lid
                if wants_blocker:
                    # the blocking blade, and the block above it, which must
                    # also refuse to be dragged
                    reg[x, BLOCK_Y, L["rest"]] = (wool if end else honey)
                    reg[x, BLOCK_Y + 1, L["rest"]] = nostick
                    for y in range(BLOCK_Y + 2, CONTAIN_Y + 1):
                        reg[x, y, L["rest"]] = stone
                else:
                    for y in range(TROUGH + 1, CONTAIN_Y + 1):
                        reg[x, y, L["rest"]] = stone

                # plant lane
                for y in range(1, SOIL):
                    reg[x, y, L["plant"]] = stone
                reg[x, SOIL, L["plant"]] = soil
                for y in range(STUB, TOP + 1):
                    reg[x, y, L["plant"]] = (bamboo_l if y == TOP else
                                             bamboo_s if y == TOP - 1 else bamboo)

            # one piston per blade, bearing on the first HONEY block
            px = first + (1 if knife_ends == "wool" else 0)
            reg[px, CUT, L["piston"]] = piston
            if wants_blocker:
                reg[px, BLOCK_Y, L["piston"]] = piston

        meta_tiers.append(dict(L, CUT=CUT, TROUGH=TROUGH, TOP=TOP,
                               blocker=wants_blocker, tier=r))

    # ---- caps: solid, with a loaded dispenser at each trough head -----------
    for cap_x in caps:
        for z in range(D):
            for y in range(1, CONTAIN_Y + 1):
                reg[cap_x, y, z] = stone
    for cap_x in caps[:-1]:
        for t in meta_tiers:
            container(reg, cap_x, t["TROUGH"], t["plant"],
                      block("dispenser", facing="east", triggered="false"),
                      [(0, "water_bucket", 1)])
            reg[cap_x - 1, t["TROUGH"], t["plant"]] = block(
                "stone_button", face="wall", facing="west",
                powered="false") if cap_x > 0 else reg[cap_x - 1,
                                                       t["TROUGH"], t["plant"]]

    # ---- drop shafts: ONE PER TIER, never shared --------------------------
    plant_lanes = {t["plant"]: t for t in meta_tiers}
    for drop_x in drops:
        for z in range(D):
            for y in range(1, CONTAIN_Y + 1):
                reg[drop_x, y, z] = stone
        for z, t in plant_lanes.items():
            for y in range(2, t["TROUGH"] + 1):
                reg[drop_x, y, z] = AIR
            reg[drop_x, 1, z] = hopper_d
            reg[drop_x, 0, z] = chest
        # the knife must not drag the shaft wall; wool ends make stone safe
        for t in meta_tiers:
            reg[drop_x, t["CUT"], t["rest"]] = stone

    # ---- firing lines ------------------------------------------------------
    # One per backing lane for the cutting knives, and a separate one for the
    # blocking blades, because they must fire LATER -- firing them with the cut
    # would catch the crop in mid-air instead of letting it land.
    piston_xs = {m * X_PITCH + 1 + (1 if knife_ends == "wool" else 0)
                 for m in range(cols)}
    ctrl_x = next(x for x in range(1, W - 1) if x not in piston_xs)

    # A backing column is shared by tiers at the SAME height (that is what
    # height_of arranges), so each one carries a single cutting line at its own
    # level. Getting this wrong is silent: the line looks continuous in the
    # schematic and the tier simply never fires.
    by_backing = {}
    for t in meta_tiers:
        by_backing.setdefault(t["backing"], []).append(t)
    def run_line(bz, y):
        """One firing line along a backing column, with the repeaters it needs.

        Dust carries 15 blocks. A 31-wide build is dead by x=17 and a 51-wide
        one long before its far end, so without these the modules past that
        point never fire -- measured here as 16 of 24 knives moving, exactly two
        modules out of three. Repeaters must not land on a piston's own backing
        block, which is where its dust has to be.
        """
        for x in range(1, W - 1):
            reg[x, y - 1, bz] = stone
            reg[x, y, bz] = dust
        reg[ctrl_x, y, bz] = lever
        x = ctrl_x + 13
        while x < W - 1:
            while x < W - 1 and x in piston_xs:
                x += 1
            if x < W - 1:
                reg[x, y, bz] = repeater
            x += 14

    for bz, ts in sorted(by_backing.items()):
        heights = {t["CUT"] for t in ts}
        assert len(heights) == 1, (
            f"backing lane {bz} shared by tiers at different heights {heights}; "
            "one column cannot carry two lines")
        run_line(bz, heights.pop() + 1)

    # The blocking blades fire LATER, so they get their own line -- two levels
    # up the same backing column, clear of the cutting line below it.
    for t in meta_tiers:
        if t["blocker"]:
            run_line(t["backing"], BLOCK_Y + 1)

    if add_sign:
        sign(reg, 1, CONTAIN_Y + 1, 0,
             ["Bamboo Terrace", VERSION, f"{tiers}x{cols} mods",
              f"{tiers*cols*columns} cols"])

    meta = dict(W=W, H=H, D=D, tiers=tiers, cols=cols, columns=columns,
                X_PITCH=X_PITCH, caps=caps, drops=drops, CUT_Y=LOW_CUT,
                BLOCK_Y=BLOCK_Y, CONTAIN_Y=CONTAIN_Y, ctrl_x=ctrl_x,
                tier_meta=meta_tiers)
    return reg, meta


reg, META = build_region()

if __name__ == "__main__":
    import sys as _s
    tiers = int(_s.argv[1]) if len(_s.argv) > 1 else 4
    cols = int(_s.argv[2]) if len(_s.argv) > 2 else 3
    reg, m = build_region(tiers=tiers, cols=cols)
    n = tiers * cols * m["columns"]
    save(reg, f"bamboo-terrace-{cols}x{tiers}",
         f"Bamboo Terrace {cols}x{tiers} {VERSION}",
         f"{n} planted columns in {m['W']}x{m['D']}; no middle walls, "
         "no slime, one shaft per tier.")
