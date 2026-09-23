"""Cart storage hall -- one chest minecart in, ten double chests filled in order.

A loaded chest minecart rolls in from the west on the user's own rail line,
brakes over a bank of hoppers, is emptied, and is kicked back out to the east.
Everything it carried walks DOWNHILL through a staircase of ten double chests.

    rail in --> boost --> detector --> [4 unloader hoppers] --> brake --> kick out
                                            |
                                            v
                                       double chest 1
                                            |  hopper
                                       double chest 2
                                            |  ...
                                       double chest 10   (no hopper: the end)

WHY A HOPPER STAIRCASE AND NOT THE FARM'S WATER TROUGH.
The bamboo farm distributes with a water stream over a row of hoppers
(plan_stream / the sump code in builds/bamboo_cascade.py) and that is the right
tool there, because the farm produces ITEM ENTITIES: broken bamboo lying on the
ground, which a current can carry PAST a hopper whose chest is already full.
This build never has an item entity. A chest minecart's cargo leaves through a
hopper as inventory, item by item, and the only way back to entity form is a
dropper plus a clock -- a clock that then has to be stopped when the cart runs
out or it spits the hall's contents onto the floor. So the water idea is
deliberately NOT reused; it would add a clock, a shut-off and a spill risk to
buy an overflow behaviour that pure hoppers already give for free.

The staircase gets the same overflow by running the chain the other way round.
Every double chest has one hopper UNDER it that pulls from it and pushes into
the NEXT chest, one block east and one block down. So nothing settles in chest 1
while there is room further along: the hall fills from chest 10 backwards. When
chest 10 is full, hopper 9 cannot push, hopper 9 fills (five stacks), chest 9
starts to hold, and so on back up the stair. When chest 1 is finally full the
unloader hoppers back up and the cart simply stops emptying. Items back up,
nothing jams, nothing spills, and the cart is still holding the remainder.

The cost of that is one block of descent per chest. The hopper under chest i
must be face-adjacent to chest i+1, and it already sits one below chest i, so
chest i+1 can only sit at that same level. Ten chests therefore span ten columns
and nine levels. There is no flatter pure-hopper arrangement: a hopper points at
exactly one block, so a "main line with a tap into each chest" cannot exist --
the tap and the line would have to be the same output.

HOPPER BUDGET. The target server allows 16 hoppers per 16x16 chunk. This build
uses 13: nine in the staircase (chest 10 needs none, it is the terminus) and
four under the cart. The whole hall is 16 x 4 in plan, so even pasted straddling
a chunk line the tally in any one chunk can only go DOWN, never above 13.

REDSTONE, and the three places its rules shaped the layout:

  * There is no hopper under the detector rail. A detector rail with a cart on
    it strongly powers the block beneath it, and a powered hopper is LOCKED --
    so the one place a hopper must not go is the one place it looks like it
    should. The detector rail sits on plain stone, purely as a take-off point
    for whatever the user wants to trigger. The hoppers live under the plain
    rail and the brake rails, neither of which carries a signal at rest.

  * The release lever's dust sits on GLASS, not stone. Dust strongly powers the
    block directly beneath it, and that block is face-adjacent to the unloader
    hoppers -- on stone, flipping the lever would lock the very hoppers doing
    the work. Glass cannot be powered, so the dust reaches the brake rails
    beside it and goes no further. The lever itself stands on stone: dust will
    sit on glass, but a lever's attachment to glass is not worth betting on.

  * The boost and kick-out rails are powered by a redstone block placed directly
    UNDER them. A redstone block does not power a plain block next to it, which
    is exactly why this is safe: the stone deck blocks either side stay
    unpowered, so the hoppers face-adjacent to them stay unlocked.

The analog-decay rule does not bite here. The lever is three blocks from the
furthest brake rail, so the weakest rail sees 13 of 15, and nothing in this
build reads a level -- only on or off.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcschem import AIR, block, region, save, sign  # noqa: E402

VERSION = "cascade-storage-v1"

N_CHESTS = 10
HOPPER_BUDGET = 16          # per 16x16 chunk, server rule

# ── plan ─────────────────────────────────────────────────────────────────────
# z lanes. The hall is only four deep: a wall to hang the rail deck and the
# control dust off, the working lane, the second half of every chest, and a
# stair you can walk down beside them.
Z_WALL, Z_MAIN, Z_HALF, Z_WALK = 0, 1, 2, 3

W, H, D = 16, 13, 4

RAIL_Y = 12                 # the track
DECK_Y = RAIL_Y - 1         # the course every rail sits on
TOP_CHEST_Y = 10            # double chest 1, directly under unloader hopper A
CHEST_X0 = 4

X_ENTRY = 0                 # plain rail: join your own line here
X_BOOST = (1, 2)            # powered rail on a redstone block
X_DETECT = 3                # detector rail, on stone, no hopper beneath
X_UNLOAD = (4, 5, 6, 7)     # hoppers under all four -- see below
X_BRAKE = (5, 6, 7)         # unpowered powered rail: this is what stops it
X_LEVER = 8
X_KICK = (9, 10)            # powered rail on a redstone block, always on

# Four unloader hoppers, not one. Two unpowered powered rails brake a cart at
# full speed inside roughly two blocks -- but "roughly" is a number measured on
# a server this build is not allowed to touch, and a cart that comes to rest one
# block past the last hopper unloads nothing at all and reports no error. Four
# hoppers make the landing zone four blocks wide and cost 4 of a 16 budget
# rather than 1. They chain west into each other and the westmost drops into
# chest 1, so wherever in the bank the cart stops, the cargo takes one path.

# type=left / type=right is read from IN FRONT of the chest: stand where it
# opens, look back at it, and the left half is the one on your left. Facing east
# means that viewer is looking west, and looking west your left hand points
# south, so the +z half is `left`. Cross-check the table against the case
# everyone knows: a chest facing north has its `left` half to the east.
# The values are the offset from the RIGHT half to the LEFT half.
LEFT_OF = {"north": (1, 0), "south": (-1, 0), "east": (0, 1), "west": (0, -1)}


def chest_x(i):
    return CHEST_X0 + i


def chest_y(i):
    return TOP_CHEST_Y - i


def hopper_y(i):
    """The hopper under chest i -- which is also the level of chest i+1."""
    return chest_y(i) - 1


def double_chest(reg, x, y, z, facing):
    """Two chest blocks the game will read as one double chest.

    Matching `facing` plus one `left` and one `right` on the correct sides is
    the whole of it. Get the sides backwards and the game still places two
    chests quite happily, renders them as a broken pair, and does not merge
    the inventory -- there is no error to see.
    """
    dx, dz = LEFT_OF[facing]
    reg[x, y, z] = block("chest", facing=facing, type="right",
                         waterlogged="false")
    reg[x + dx, y, z + dz] = block("chest", facing=facing, type="left",
                                   waterlogged="false")
    return [(x, y, z), (x + dx, y, z + dz)]


def build_region(add_sign=True, fill="stone"):
    reg = region(W, H, D)

    stone = block(fill)
    glass = block("glass")
    rblock = block("redstone_block")

    rail = block("rail", shape="east_west", waterlogged="false")
    # `powered` is recomputed on the first block update, but shipping each rail
    # in the state it will actually settle into means a reader of the schematic
    # can see at a glance which rails are live and which one is the brake.
    prail_on = block("powered_rail", shape="east_west", powered="true",
                     waterlogged="false")
    prail_off = block("powered_rail", shape="east_west", powered="false",
                      waterlogged="false")
    drail = block("detector_rail", shape="east_west", powered="false",
                  waterlogged="false")

    dust = block("redstone_wire", north="side", south="side",
                 east="side", west="side", power="0")
    lever = block("lever", face="floor", facing="north", powered="false")

    def hopper(facing):
        return block("hopper", facing=facing, enabled="true")

    for x in range(W):
        for y in range(H):
            for z in range(D):
                reg[x, y, z] = AIR

    # ---- floor and back wall -----------------------------------------------
    # The wall is what the rail deck hangs off. Without it the deck is a line of
    # blocks floating over the stair: it places perfectly well and reads as a
    # mistake, which is its own kind of bug report.
    for x in range(W):
        for z in range(D):
            reg[x, 0, z] = stone
        for y in range(0, DECK_Y + 1):
            reg[x, y, Z_WALL] = stone

    # ---- the staircase of double chests -------------------------------------
    chests, hoppers = [], []
    for i in range(N_CHESTS):
        x, cy, hy = chest_x(i), chest_y(i), hopper_y(i)

        # The solid step under this chest: the working lane, the landing under
        # the second half, and the tread you walk on. The tread top is one below
        # the chest, so you stand level with the chest you are opening.
        for z in (Z_MAIN, Z_HALF, Z_WALK):
            for y in range(0, hy + 1):
                reg[x, y, z] = stone

        # Facing east so every chest front looks down the stair into open air.
        # Facing west would point it straight at the hopper feeding it -- which
        # works, a chest only needs a non-opaque block ABOVE it to open, but it
        # reads as an accident. The pair runs along z because a chest's pair
        # axis is perpendicular to its facing, and the stair already owns the x
        # axis at one column per chest.
        chests += double_chest(reg, x, cy, Z_MAIN, "east")

        if i < N_CHESTS - 1:
            # Pulls from the chest above it, pushes east into the next chest,
            # which sits at exactly this level. Chest 10 gets no hopper: it is
            # the end of the line, and a hopper there would have nowhere to
            # push and would simply hold five stacks out of reach.
            reg[x, hy, Z_MAIN] = hopper("east")
            hoppers.append((x, hy, Z_MAIN))

    # ---- the west landing ---------------------------------------------------
    for x in range(0, CHEST_X0):
        for z in (Z_MAIN, Z_HALF, Z_WALK):
            for y in range(0, DECK_Y):
                reg[x, y, z] = stone

    # ---- the rail deck ------------------------------------------------------
    # Every rail needs something solid directly beneath it. Along the working
    # lane that is stone, except where a redstone block powers a rail or a
    # hopper carries one -- rails sit on hoppers quite happily, which is the
    # whole reason a cart can be emptied where it stands.
    for x in range(W):
        if reg[x, DECK_Y, Z_MAIN].id == "minecraft:air":
            reg[x, DECK_Y, Z_MAIN] = stone

    for x in X_BOOST + X_KICK:
        reg[x, DECK_Y, Z_MAIN] = rblock

    for x in X_UNLOAD:
        if x == X_UNLOAD[0]:
            reg[x, DECK_Y, Z_MAIN] = hopper("down")      # into chest 1
        else:
            reg[x, DECK_Y, Z_MAIN] = hopper("west")      # along the bank
        hoppers.append((x, DECK_Y, Z_MAIN))

    # ---- the track ----------------------------------------------------------
    for x in range(W):
        reg[x, RAIL_Y, Z_MAIN] = rail
    for x in X_BOOST + X_KICK:
        reg[x, RAIL_Y, Z_MAIN] = prail_on
    reg[X_DETECT, RAIL_Y, Z_MAIN] = drail
    for x in X_BRAKE:
        # Unpowered, so it brakes. These three are the only thing holding the
        # cart; the lever turns all three into boosters at once and it leaves
        # east over the kick rails.
        reg[x, RAIL_Y, Z_MAIN] = prail_off

    # ---- the release control ------------------------------------------------
    # Glass under the dust, stone under the lever. See the module docstring:
    # dust on stone here would power the deck blocks beside the hoppers and lock
    # them the instant the lever went on.
    for x in X_BRAKE:
        reg[x, DECK_Y, Z_WALL] = glass
        reg[x, RAIL_Y, Z_WALL] = dust
    reg[X_LEVER, DECK_Y, Z_WALL] = stone
    reg[X_LEVER, RAIL_Y, Z_WALL] = lever

    if add_sign:
        # rotation 0 faces south, toward the walkway, which is the only side of
        # this hall anyone ever stands on.
        sign(reg, 0, DECK_Y, Z_WALK,
             ["Cart Storage", VERSION, "10 double chests", "13 hoppers"],
             rotation=0)

    m = dict(W=W, H=H, D=D, chests=chests, hoppers=hoppers,
             rail_y=RAIL_Y, deck_y=DECK_Y, z_main=Z_MAIN,
             unload=list(X_UNLOAD), brake=list(X_BRAKE),
             detect=X_DETECT, boost=list(X_BOOST), kick=list(X_KICK),
             entry=X_ENTRY, lever=X_LEVER,
             chest_x=chest_x, chest_y=chest_y, hopper_y=hopper_y)
    return reg, m


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments"))
    from check_wiring import check  # noqa: E402

    reg, m = build_region()
    if check(reg, "cart storage"):
        raise SystemExit("unsupported redstone -- not saving")

    save(reg, VERSION, "Cart Storage Hall",
         f"{VERSION} -- chest minecart unloader into {N_CHESTS} double chests")
    print(f"  {len(m['hoppers'])} hoppers (budget {HOPPER_BUDGET}/chunk), "
          f"{len(m['chests'])} chest blocks = {len(m['chests']) // 2} doubles")
