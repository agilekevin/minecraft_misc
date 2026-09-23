"""Bamboo harvester — honey cuts and catches, one water pulse sweeps it out.

The honey caps the fall path, so drops land on it instead of scattering to the
ground. When extended it is also the FLOOR OF A CHANNEL: the walls either side
start one block above it, so a single dispenser pulse runs the length of the
trough and pours off the far end, taking the crop with it.

Sequence, driven by hand for now:

  1. Flip the lever. The honey row moves into the plant column, destroying the
     segment at CUT_Y; everything above loses support and lands on the honey.
     The honey now also caps the plant column, which is what makes step 2 safe.
  2. Press the button. The dispenser places a water source at the head of the
     trough; it runs the length of the honey and pours off the end.
  3. Press the button again. The emptied bucket picks the source back up.
  4. Flip the lever back.

STEP 3 IS LIFE SUPPORT, NOT HOUSEKEEPING. Measured on a headless 1.21.8 server:

  * Water does NOT destroy bamboo. A source directly above it, or flowing into
    it from the side, leaves it standing. (I assumed the opposite for a long
    time. It is not true.)
  * A FLOODED COLUMN IS STERILE. A dry control grew from 1 segment to 13 under
    the same tick load; a column with water above it stayed at 1 and never
    moved.
  * Honey moves freely with a water source sitting on it — pushing AND pulling,
    verified with the water confirmed present at the instant the piston fired.

Together those say the machine does not fail safe. Nothing stops you retracting
while the trough is full, and the damage is not a jam or a smashed farm — it is
a farm that looks perfectly healthy, keeps its stubs, and silently never grows
again. Any automation MUST guarantee the drain completes before the retract.

Item entities also FLOAT, so nothing sinks into a hopper while the water is in.
Draining is what drops them. Conveniently that is the same action as above.

WHY EIGHT COLUMNS. A water source reaches seven blocks, so a source plus its
flow is exactly eight tiles — confirmed in game: all 8 trough tiles wet from one
source. Sizing to that means one dispenser covers the row with nothing left dry.
It also drops the push to 8 blocks, well under the 12-block piston limit.

MEASURED RECOVERY: 71 of 72 possible bamboo actually drop; 64 reach the chest.
The ~10% that does not is structural — those items drop BELOW the honey shelf,
level with the stub, where a wash running along the top of the honey can never
reach them. See seal_far_void for the part of that which is recoverable.

THE ADJACENCY RULES. Honey drags every face-adjacent movable block in the
direction it travels. One extra block is silent: the piston simply does not
move, with no error and no clue. So:

  * Nothing sits directly under the honey at rest.
  * The channel walls START ONE BLOCK ABOVE the honey. At the honey's own level
    they would be face-adjacent to the extended row and jam the retract.
  * The END CAPS use SLIME wherever they would touch the row. Slime and honey
    are the one pair that does not stick, so slime holds the wall without
    joining the push; stone there would take the whole cap with it.

Cross-section (+z is south; the trough runs east along z=3):

    z=0  piston backing and lever
    z=1  sticky piston at CUT_Y (west end only; air elsewhere at that level)
    z=2  honey row at CUT_Y, slime lid above (the near channel wall)
    z=3  PLANT - soil, then bamboo; honey enters here; trough runs on top
    z=4  far channel wall, from one block above the honey upward

The two controls sit on different faces, which is worth knowing before you go
looking: the LEVER is on the north side at z=0, because it has to sit on the
block behind the piston to power it; the BUTTON is on the west face at x=0,
because that is the only side of the cap the dispenser can be reached from.

The last planted column is followed by an unplanted one: the honey stops short,
the trough runs out of floor, and the crop falls to the hoppers. A stream
running orthogonally can replace them later.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcschem import AIR, block, container, region, save, sign  # noqa: E402

VERSION = "v1.6"


def build_region(columns=8, cut_y=5, top_y=13, contain_extra=0,
                 seal_far_void=True, lid="slime", shelf_wall=True,
                 knife_ends="wool", nonstick="obsidian",
                 add_sign=True):
    """The design, parameterised so experiments can sweep it.

    Everything that varies lives here rather than in a separate test copy, so
    what gets measured on the server is always what gets pasted into the world.

    seal_far_void: fill z=4 from y=1 up to CUT_Y-1. That void was open in v1.0
        and measured drops fall down it to the floor, out of reach. On over six
        harvests it is worth 1-2 bamboo -- a small effect whose range overlaps
        the baseline's, so not the 5.5-point win a single run suggested, but it
        costs nothing but stone in a space that was already empty. Default on.
        The fill stops BELOW the honey's own level, so it never touches the
        extended row and cannot jam the retract.
    """
    CUT_Y = cut_y
    TOP_Y = top_y
    WATER_Y = CUT_Y + 1
    CONTAIN_Y = TOP_Y + contain_extra

    # x=0 button | x=1 cap + dispenser | planted | drop column | cap
    W, H, D = columns + 4, CONTAIN_Y + 2, 5
    CAP_X = 1
    LANE = range(2, columns + 2)
    DROP_X = columns + 2

    reg = region(W, H, D)

    stone = block("stone")
    soil = block("dirt")
    bamboo = block("bamboo", age="0", leaves="none", stage="0")
    bamboo_small = block("bamboo", age="0", leaves="small", stage="0")
    bamboo_large = block("bamboo", age="0", leaves="large", stage="0")
    honey = block("honey_block")
    # The two blocks that must touch the honey WITHOUT being dragged: the lid
    # sitting on it, and the wall at its own level. Slime works because honey
    # does not stick to it. IMMOVABLE blocks work for a different reason --
    # measured, honey simply fails to drag them and moves anyway, so obsidian
    # does the same job with no slime farm involved.
    slime = block(nonstick)
    wool = block("orange_wool")
    sticky = block("sticky_piston", facing="south", extended="false")
    dispenser = block("dispenser", facing="east", triggered="false")
    hopper_d = block("hopper", facing="down", enabled="true")
    chest = block("chest", facing="north", type="single")
    lever = block("lever", face="floor", facing="north", powered="false")
    # Wall-mounted on the dispenser's west face, so it is pressed from outside.
    # The dispenser has to sit INSIDE the cap to fire along the trough, so a
    # button on top of it would be sealed in stone with no way to reach it.
    button = block("stone_button", face="wall", facing="west", powered="false")

    for x in range(W):
        for z in range(D):
            for y in range(H):
                reg[x, y, z] = AIR
            reg[x, 0, z] = stone

    for x in LANE:
        # z=1  piston lane. Air at CUT_Y except at the piston, or it is dragged.
        for y in range(1, CUT_Y):
            reg[x, y, 1] = stone

        # z=2  honey rest column. Stone stops one short of the honey: a block
        #      directly beneath is face-adjacent and would join the push.
        for y in range(1, CUT_Y - 1):
            reg[x, y, 2] = stone
        # THE HONEY KNIFE: the row that is driven into the bamboo.
        #
        # knife_ends="wool" swaps the two end blocks for something non-sticky.
        # Honey drags whatever it touches, but a plain block that is BEING
        # dragged does not grip its own neighbours -- so wool ends ride along
        # with the knife while touching the caps without pulling on them, and
        # the caps can go back to plain stone instead of slime.
        if knife_ends == "wool" and x in (LANE.start, LANE.stop - 1):
            reg[x, CUT_Y, 2] = wool
        else:
            reg[x, CUT_Y, 2] = honey
        # The near channel wall, starting one block above the honey. Slime at
        # the bottom course because that block sits directly ON the honey, and
        # slime is the one thing honey does not stick to.
        # The lid is the ONE block that sits directly on the honey, and it is
        # the single biggest material cost of a grid: 200 slime blocks (2565
        # slimeballs) for a 5x5. Stone there sticks to the honey and jams the
        # push -- measured, the piston simply never fires. Air does not jam, but
        # leaves the trough's north bank open at exactly the water's level.
        for y in range(WATER_Y, CONTAIN_Y + 1):
            if y != WATER_Y:
                reg[x, y, 2] = stone
            elif lid == "slime":
                reg[x, y, 2] = slime
            elif lid == "stone":
                reg[x, y, 2] = stone
            # lid == "air": left open, deliberately

        # z=3  the plant. The trough runs above this, on the honey's top face.
        for y in range(1, 3):
            reg[x, y, 3] = stone
        reg[x, 3, 3] = soil
        for y in range(4, TOP_Y + 1):
            reg[x, y, 3] = (bamboo_large if y == TOP_Y
                            else bamboo_small if y == TOP_Y - 1 else bamboo)

        # z=4  far channel wall from WATER_Y up.
        if seal_far_void:
            for y in range(1, CUT_Y):
                reg[x, y, 4] = stone
        # CUT_Y itself is normally left open, because a block level with the
        # extended honey gets dragged and jams the retract. That gap is where
        # the last of the crop is lost: measured, 6 of 70 scatter sideways off
        # the shelf into this lane at drop time and sit one level below the
        # wash, which can never reach them.
        #
        # SLIME closes it without jamming anything -- honey does not stick to
        # slime, the same property the lid and the end caps rely on.
        if shelf_wall:
            reg[x, CUT_Y, 4] = slime
        for y in range(WATER_Y, CONTAIN_Y + 1):
            reg[x, y, 4] = stone

    # Where the knife's ENDS touch the structure. With wool ends nothing
    # there sticks to the knife, so plain stone will do.
    end_block = stone if knife_ends == "wool" else slime

    # --- the drop column ----------------------------------------------------
    for y in range(1, CONTAIN_Y + 1):
        reg[DROP_X, y, 1] = stone
        reg[DROP_X, y, 4] = stone
        # Slime at the honey's own level: stone there is face-adjacent to the
        # last honey block and would be dragged into the push.
        reg[DROP_X, y, 2] = end_block if y == CUT_Y else stone
    reg[DROP_X, 1, 3] = hopper_d
    reg[DROP_X, 0, 3] = chest

    # --- end caps -----------------------------------------------------------
    for x in (CAP_X, W - 1):
        for z in range(D):
            for y in range(1, CONTAIN_Y + 1):
                reg[x, y, z] = end_block if (y == CUT_Y and z in (2, 3)) else stone

    # --- piston, lever, dispenser -------------------------------------------
    # The piston has to bear on a HONEY block. Pushing a wool end would move
    # the wool and leave the knife standing, since wool cannot drag honey.
    piston_x = LANE.start + 1 if knife_ends == "wool" else LANE.start
    reg[piston_x, CUT_Y, 1] = sticky
    reg[piston_x, CUT_Y, 0] = stone
    reg[piston_x, WATER_Y, 0] = lever

    # Dispenser buried in the west cap at the head of the trough, firing east
    # along the honey's top face. Load it with a water bucket: one press places
    # the source, the next picks it back up with the emptied bucket.
    container(reg, CAP_X, WATER_Y, 3, dispenser, [(0, "water_bucket", 1)])
    reg[CAP_X - 1, WATER_Y, 3] = button

    if add_sign:
        sign(reg, LANE.start, CONTAIN_Y + 1, 4,
             ["Bamboo Wash", VERSION, f"{columns} cols", "load disp: water"])

    meta = dict(columns=columns, CUT_Y=CUT_Y, TOP_Y=TOP_Y, WATER_Y=WATER_Y,
                CONTAIN_Y=CONTAIN_Y, W=W, H=H, D=D, CAP_X=CAP_X,
                LANE=LANE, DROP_X=DROP_X, seal_far_void=seal_far_void,
                lid=lid, shelf_wall=shelf_wall, nonstick=nonstick,
                knife_ends=knife_ends, piston_x=piston_x)
    return reg, meta


# Module-level defaults, so every existing caller keeps working unchanged.
reg, _META = build_region()
globals().update(_META)
COLUMNS = _META["columns"]

if __name__ == "__main__":
    save(reg, "bamboo-wash", f"Bamboo Wash Harvester {VERSION}",
         f"{COLUMNS} columns sized to one water source. Lever extends, button "
         "pulses water, button again retrieves it, lever retracts.")
