"""A 32x32 section: two farms facing each other across a central corridor.

Exactly four chunks, aligned to chunk lines, so a section loads and unloads as a
unit and sections tile against each other without overlapping.

    z 0..14    farm A: fan at the north edge, crop rows, collection at z=12..14
    z 15,16    the corridor -- walk down the middle, both farms either side
    z 17..31   farm B, the same build mirrored

    32 wide  x  32 deep  x  61 tall     432 plants     12 hoppers

Why nine rows and not ten: ten rows makes each farm 16 deep, which fills the
32 exactly and leaves nothing to stand in. Nine gives back the corridor at the
cost of 48 plants.

MIRRORING IS NOT JUST COPYING. Every block whose behaviour depends on which way
it points has to be flipped as it crosses: the dispenser that fires the fan, all
the sticky pistons, every wall torch on the tower, the comparators and repeaters
in the feeds. Copy them unflipped and farm B pastes perfectly and then fires its
blades the wrong way, which is the kind of fault that only shows up in the world.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bamboo_cascade import build_region                        # noqa: E402
from mcschem import AIR, block, region, save                   # noqa: E402

ROWS, COLS, BX = 9, 3, 7          # bx=7 puts a 24-wide crop at exactly W=32
GAP = 2                           # the corridor

# north and south swap when a build is mirrored across z; east and west do not
FLIP = {"north": "south", "south": "north"}
# a standing sign's rotation is 16 points clockwise from south
FLIP_ROT = {str(r): str((8 - r) % 16) for r in range(16)}


def _mirror(state):
    """The same block, turned to face the other way along z."""
    props = dict(state.properties())
    if not props:
        return state
    if props.get("facing") in FLIP:
        props["facing"] = FLIP[props["facing"]]
    if "rotation" in props:
        props["rotation"] = FLIP_ROT.get(props["rotation"], props["rotation"])
    return block(state.id.split(":")[1], **props)


def build_section():
    a, m = build_region(rows=ROWS, cols=COLS, add_sign=False, bx=BX)
    W, H, D = m["W"], m["H"], m["D"]
    depth = 2 * D + GAP
    sec = region(W, H, depth)
    for x in range(W):
        for y in range(H):
            for z in range(depth):
                sec[x, y, z] = AIR

    # farm A, as built
    for x in range(W):
        for y in range(H):
            for z in range(D):
                sec[x, y, z] = a[x, y, z]

    # farm B, mirrored: its front meets A's front across the corridor
    for x in range(W):
        for y in range(H):
            for z in range(D):
                sec[x, y, depth - 1 - z] = _mirror(a[x, y, z])

    # a floor to stand on in the corridor, level with the bottom crop lane
    floor = block("stone")
    for x in range(W):
        for z in range(D, D + GAP):
            sec[x, m["base"] - 1, z] = floor

    return sec, m, depth


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments"))
    from check_wiring import check                              # noqa: E402

    sec, m, depth = build_section()
    W, H = m["W"], m["H"]
    bad = check(sec, "section")
    n = sum(1 for x in range(W) for y in range(H) for z in range(depth)
            if sec[x, y, z].id != "minecraft:air")
    plants = 2 * ROWS * m["width"]
    print(f"  {W} x {H} x {depth}   ({W // 16} x {depth // 16} chunks)")
    print(f"  {n} blocks, {plants} plants, {2 * len(m['hoppers'])} hoppers, "
          f"{2 * len(m['hoppers']) / (W * depth / 256):.1f} per chunk")
    save(sec, "cascade-section-2x2", "Bamboo cascade, 2x2 chunk section",
         f"two {ROWS}-row farms front to front, {plants} plants")
