"""Tile the harvester into a grid. Sharing walls is most of the win.

A lone module is 12x5 on the ground for 8 productive columns -- 7.5 ground
blocks per column. Almost all of that waste is in the z direction, where 5 rows
of structure support a SINGLE row of plants. Tiling attacks exactly that.

THREE THINGS GET SHARED.

1. THE MIDDLE WALL, between mirrored rows. Row 0 faces south and ends in a
   wall; row 1 is its mirror image and starts with the same wall. One wall, two
   troughs -- it is the north bank of one and the south bank of the other.

   Named for where it sits: the lane between two rows' EXTENDED honey. Its
   profile, bottom to top, is stone foundation / SLIME at the honey's own level
   / stone the rest of the way up. The slime course is the whole reason the
   wall can exist at that height: stone there is dragged by the honey and jams
   the retract, which is why the level used to be left open, and why closing it
   moved recovery from 90.7% to 98.1%.

   With an odd number of rows the last wall is an EDGE wall rather than a
   middle one -- crop on one side of it only -- but it is built identically.

2. THE BACKING COLUMN, between row pairs. Row 1's piston faces north and needs a
   solid block behind it; row 2's faces south and needs one too. Put them back to
   back and a single column serves both, and a single redstone line through it
   fires both rows at once.

3. THE CAP, as the east wall of the previous module's drop shaft.

That collapses the z period from 5 blocks per row to 4, and the x period from 12
per module to 10:

    z:  firing | piston | rest | PLANT | MIDDLE | PLANT | rest | piston | firing
         lane  |  lane  | lane |  lane |  WALL  |  lane | lane |  lane |  lane
               <------- row 0 -------> shared <------- row 1 ------->    shared

    Vocabulary used throughout:
      firing lane  the backing blocks with the redstone line along their top
      piston lane  holds one sticky piston per module; empty at the cut level
      rest lane    where the honey parks, with the SLIME LID sitting on it
      plant lane   soil, stub and bamboo; the trough runs on the honey above it
      middle wall  between two rows' extended honey; slime at the honey's level
      cap          the solid column at a module's west end, holding a dispenser
      drop shaft   the open column the trough pours into, over the trench

    x:  cap | 8 x PLANT | drop | cap | 8 x PLANT | drop | cap ...

For a 5x5 that is 51 x 23 = 1173 ground for 200 columns, 5.9 per column against
7.5 standing alone -- about a fifth less ground for the same crop.

CONTROL IS THE REAL REASON TO TILE. Twenty-five separate levers and twenty-five
buttons is not a farm, it is a chore. Every piston in a row pair sits against one
shared backing column, so one redstone line per pair fires five modules at once,
and three lines cover all twenty-five.

COLLECTION reuses the pattern that got 109 out of the twelve-column build: a
north-south trench behind each column of modules, water pushed in from both ends,
and a short run of hoppers where the two flows meet and stall. Five module
columns means five trenches and five chests -- not twenty-five.

WHAT IS NOT DONE HERE. The dispensers are placed but not wired: each still wants
its own button. Wiring them means either a redstone bus through solid cap
columns, or dropping dispensers entirely for a piston-operated water gate (a
source in a niche, a piston pushing a block in front of it to cut the flow --
which needs no buckets and rides the same kind of line as the main pistons).
That is the obvious next step and it is untested, so it is not built in.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcschem import AIR, block, container, region, save, sign  # noqa: E402

VERSION = "grid-v0.6"


def row_layout(r):
    """z positions for row r. Even rows face south, odd rows are mirrored.

    The mirroring is what lets consecutive rows share a wall AND lets each pair
    share a backing column with the next pair.
    """
    base = 4 * r + 1                       # +1: z=0 is the trench's end wall
    if r % 2 == 0:
        return dict(backing=base, piston=base + 1, honey=base + 2,
                    plant=base + 3, wall=base + 4, facing="south")
    return dict(wall=base, plant=base + 1, honey=base + 2,
                piston=base + 3, backing=base + 4, facing="north")


def build_grid(rows=5, cols=5, columns=8, cut_y=5, top_y=13,
               stall=4, cap_fill="slime", knife_ends="wool",
               nonstick="obsidian", add_sign=True):
    CUT_Y, TOP_Y = cut_y, top_y
    WATER_Y = CUT_Y + 1
    CONTAIN_Y = TOP_Y

    X_PITCH = columns + 2                  # cap + planted + drop shaft
    W = cols * X_PITCH + 1                 # +1: a final east cap
    D = rows * 4 + 3                       # +3: two trench end walls, +1 wall
    H = CONTAIN_Y + 2

    reg = region(W, H, D)

    stone = block("stone")
    soil = block("dirt")
    bamboo = block("bamboo", age="0", leaves="none", stage="0")
    bamboo_s = block("bamboo", age="0", leaves="small", stage="0")
    bamboo_l = block("bamboo", age="0", leaves="large", stage="0")
    honey = block("honey_block")
    # Whatever can touch the honey without being dragged. Slime works because
    # honey will not stick to it; an IMMOVABLE block works because honey cannot
    # take it along and gives up trying. Both leave the push set at 8.
    slime = block(nonstick)
    # Marks the knife's ends, and is deliberately a colour you can spot.
    wool = block("orange_wool")
    water = block("water", level="0")
    chest = block("chest", facing="west", type="single")
    dust = block("redstone_wire", east="side", west="side",
                 north="side", south="side", power="0")
    lever = block("lever", face="floor", facing="north", powered="false")
    # On the OUTSIDE north face of the west cap, where a player can reach it.
    wbutton = block("stone_button", face="wall", facing="north",
                    powered="false")
    # A repeater's `facing` points at its INPUT side, not its output -- measured,
    # after facing="east" silently swallowed the signal and every module east of
    # the first repeater failed to fire. Signal travels east, so it faces west.
    repeater = block("repeater", facing="west", delay="1",
                     locked="false", powered="false")
    # Same rule, rotated: a line running south (+z) is fed from the north.
    repeater_south = block("repeater", facing="north", delay="1",
                           locked="false", powered="false")

    def piston(facing):
        return block("sticky_piston", facing=facing, extended="false")

    def dispenser():
        return block("dispenser", facing="east", triggered="false")

    def hopper(facing):
        return block("hopper", facing=facing, enabled="true")

    for x in range(W):
        for z in range(D):
            for y in range(H):
                reg[x, y, z] = AIR
            reg[x, 0, z] = stone

    rowinfo = [row_layout(r) for r in range(rows)]
    caps = [m * X_PITCH for m in range(cols)] + [cols * X_PITCH]
    drops = [m * X_PITCH + columns + 1 for m in range(cols)]

    # ---- the module rows ---------------------------------------------------
    for r, L in enumerate(rowinfo):
        for m in range(cols):
            first = m * X_PITCH + 1
            lane = range(first, first + columns)

            for x in lane:
                # backing: solid THROUGH the piston's level. The firing line
                # rides on top of it -- see the firing-line section for why that
                # is the arrangement that actually works.
                for y in range(1, CUT_Y + 1):
                    reg[x, y, L["backing"]] = stone

                # piston lane: air at CUT_Y, or the honey drags it along
                for y in range(1, CUT_Y):
                    reg[x, y, L["piston"]] = stone

                # honey rest: stone stops TWO short, so nothing sits directly
                # beneath the honey to be dragged into the push
                for y in range(1, CUT_Y - 1):
                    reg[x, y, L["honey"]] = stone
                # THE HONEY KNIFE -- the row driven into the bamboo.
                #
                # Its END blocks are wool. Honey drags whatever it touches, but
                # a plain block being dragged does not grip ITS neighbours, so
                # wool ends ride along with the knife while touching the caps
                # without pulling on them. That lets the caps and drop shafts be
                # plain stone instead of slime. Measured: still extends and
                # retracts every time, recovery unchanged or slightly better,
                # and it saves every end-slime block in the build.
                if knife_ends == "wool" and x in (first, first + columns - 1):
                    reg[x, CUT_Y, L["honey"]] = wool
                else:
                    reg[x, CUT_Y, L["honey"]] = honey
                reg[x, WATER_Y, L["honey"]] = slime      # sits ON the honey
                for y in range(WATER_Y + 1, CONTAIN_Y + 1):
                    reg[x, y, L["honey"]] = stone

                # the plant, with the trough running above it on the honey
                for y in (1, 2):
                    reg[x, y, L["plant"]] = stone
                reg[x, 3, L["plant"]] = soil
                for y in range(4, TOP_Y + 1):
                    reg[x, y, L["plant"]] = (bamboo_l if y == TOP_Y else
                                             bamboo_s if y == TOP_Y - 1 else bamboo)

                # The shared wall, filled BELOW the honey's level to close the
                # void that drops fall down.
                for y in range(1, CUT_Y):
                    reg[x, y, L["wall"]] = stone
                # At CUT_Y itself: SLIME, not stone and not air. Stone here is
                # level with the extended honey and jams the retract, which is
                # why this was left open. But open is where the last of the crop
                # goes -- it bounces off the side of the shelf as the bamboo
                # breaks and lands a level under the water. Slime closes it
                # without sticking to the honey: 90.7% -> 98.1% recovery.
                #
                # The wall is shared between two mirrored rows, so this one
                # course serves both of their shelves.
                reg[x, CUT_Y, L["wall"]] = slime
                for y in range(WATER_Y, CONTAIN_Y + 1):
                    reg[x, y, L["wall"]] = stone

            # One sticky piston per module drives the whole row via honey-to-
            # honey adhesion. With wool ends it must sit against the first
            # HONEY block: pushing a wool end moves the wool and leaves the
            # knife standing, because wool cannot drag honey.
            reg[first + (1 if knife_ends == "wool" else 0),
                CUT_Y, L["piston"]] = piston(L["facing"])

    # ---- caps --------------------------------------------------------------
    for cap_x in caps:
        for z in range(D):
            for y in range(1, CONTAIN_Y + 1):
                reg[cap_x, y, z] = stone
        for L in rowinfo:
            # These two blocks sit beside the ENDS of the honey row. Stone here
            # is dragged along and jams the push; slime is the one solid that
            # honey does not stick to. Air also does not jam -- cap_fill="air"
            # tests whether the slime is doing anything the emptiness would not.
            # Nothing sticks to the knife here once its ends are wool.
            end = (stone if knife_ends == "wool"
                   else slime if cap_fill == "slime" else AIR)
            reg[cap_x, CUT_Y, L["honey"]] = end
            reg[cap_x, CUT_Y, L["plant"]] = end
    for cap_x in caps[:-1]:
        for L in rowinfo:
            # Loaded with a water bucket. Whether the inventory survives the
            # paste depends on Litematica's NBT settings, so the build notes
            # carry a one-command loader for when it arrives empty.
            container(reg, cap_x, WATER_Y, L["plant"], dispenser(),
                      [(0, "water_bucket", 1)])

    # ---- drop shafts and the collection trench -----------------------------
    # One north-south trench per column of modules. Water is pushed in from both
    # ends; the two flows meet in the middle and stall, and a short hopper run
    # under the stall zone catches what stops there.
    mid = D // 2
    stall_zone = range(mid - stall // 2, mid + (stall + 1) // 2)
    plant_lanes = {L["plant"] for L in rowinfo}
    for drop_x in drops:
        for z in range(D):
            for y in range(1, CONTAIN_Y + 1):
                reg[drop_x, y, z] = stone
        for z in range(1, D - 1):
            reg[drop_x, 1, z] = stone          # trench floor
            reg[drop_x, 2, z] = AIR            # the channel itself
            # Open the shaft ONLY above the plant lanes. Leaving the whole
            # column hollow looks harmless but removes the support the firing
            # line needs to cross it, silently cutting every row's wiring.
            if z in plant_lanes:
                for y in range(3, CONTAIN_Y + 1):
                    reg[drop_x, y, z] = AIR
        # the honey must not drag the shaft wall along with it
        for L in rowinfo:
            reg[drop_x, CUT_Y, L["honey"]] = (
                stone if knife_ends == "wool"
                else slime if cap_fill == "slime" else AIR)
        # hoppers chain toward the middle of the stall zone, into one chest
        target = mid
        for z in stall_zone:
            reg[drop_x, 1, z] = (hopper("down") if z == target
                                 else hopper("south") if z < target
                                 else hopper("north"))
        reg[drop_x, 0, target] = chest
        reg[drop_x, 2, 1] = water
        reg[drop_x, 2, D - 2] = water

    # ---- firing lines ------------------------------------------------------
    # Written LAST, and deliberately so: caps and drop shafts are solid stone
    # through the backing lanes, so a line drawn before them is overwritten at
    # every module boundary. The break is invisible in the schematic and shows
    # up in game as rows that simply never fire.
    # The dust rides ON TOP of the backing blocks, one level above the pistons.
    #
    # This was measured, after getting it wrong twice. Dust laid IN LINE beside
    # the pistons does not work: a straight run reads north=none/south=none, so
    # it never points at the piston and never powers it -- with signal strength
    # 6 sitting right beside it. Dust on top of the backing block DOES fire the
    # piston, from six blocks down the line. So does dust laid on the piston
    # itself; dust a level below does not.
    #
    # Written LAST, deliberately: caps and drop shafts are solid stone through
    # the backing lanes, so a line drawn before them is overwritten at every
    # module boundary. That break is invisible in the schematic and shows up in
    # game as rows that simply never fire.
    # Two more things this line needs, both found by watching modules fail to
    # fire on the server rather than by reading the layout.
    #
    # THE CONTROL MUST NOT SIT ON A PISTON'S BACKING BLOCK. Every module's
    # piston is at x = m*X_PITCH + 1, and whatever occupies the slot above its
    # backing block replaces the dust there. Put the lever at x=1 and module 0
    # is the one module that never fires, while every other module works --
    # which reads like a wiring fault anywhere except where it actually is.
    #
    # REPEATERS, BECAUSE DUST ONLY CARRIES 15 BLOCKS. Measured: from a source at
    # x=1 the signal is gone by x=17. A 5x5's line is 49 blocks long, so without
    # repeaters the far modules simply never fire no matter how correct the rest
    # of the wiring is.
    piston_offset = 2 if knife_ends == "wool" else 1
    piston_xs = {mi * X_PITCH + piston_offset for mi in range(cols)}
    ctrl_x = next(x for x in range(1, W - 1) if x not in piston_xs)

    for bz in sorted({L["backing"] for L in rowinfo}):
        for x in range(1, W - 1):
            reg[x, CUT_Y, bz] = stone              # the line needs a floor
            reg[x, CUT_Y + 1, bz] = dust
        # The backing lane is open above, so a control here is reachable --
        # unlike a lever buried in a cap, which is what the first draft did.
        reg[ctrl_x, CUT_Y + 1, bz] = lever
        x = ctrl_x + 13
        while x < W - 1:
            while x < W - 1 and x in piston_xs:
                x += 1                             # never displace a piston's dust
            if x < W - 1:
                reg[x, CUT_Y + 1, bz] = repeater
            x += 14

    # ---- the water bus -----------------------------------------------------
    # One button fires every dispenser. Without this the grid has no way to
    # trigger the wash at all: the dispensers sit buried at y=WATER_Y inside
    # solid cap columns, with no reachable face and nothing wired to them.
    #
    # The line rides at BUS_Y on top of the cap stone and DIPS one level at each
    # plant lane, so the dust comes to rest directly on top of that lane's
    # dispenser -- which is what fires it. Redstone climbs and descends a level
    # at a time, so the dip also carries the signal on to the next row.
    #
    # It runs two levels above the piston firing lines with solid stone between,
    # so the two controls cannot leak into one another.
    BUS_Y = WATER_Y + 2
    plant_lanes = {L["plant"] for L in rowinfo}
    honey_bus_z = rowinfo[0]["honey"]

    for cap_x in caps[:-1]:
        for z in range(D):
            if z in plant_lanes:
                reg[cap_x, WATER_Y + 1, z] = dust      # rests on the dispenser
                reg[cap_x, BUS_Y, z] = AIR             # headroom for the dip
            else:
                reg[cap_x, WATER_Y + 1, z] = stone
                reg[cap_x, BUS_Y, z] = dust
            reg[cap_x, BUS_Y + 1, z] = AIR

    # The spine joining the cap columns. It runs along row 0's honey lane, which
    # is solid stone at this height in every column -- the planted lanes are full
    # of bamboo up there and cannot carry a wire.
    for x in range(caps[0], caps[-1] + 1):
        if x in caps[:-1]:
            continue
        reg[x, WATER_Y + 1, honey_bus_z] = stone
        reg[x, BUS_Y, honey_bus_z] = dust
        reg[x, BUS_Y + 1, honey_bus_z] = AIR

    # Repeaters. Measured decay showed why spacing them evenly along the spine
    # is not enough: the spine arrives at the second cap at strength 4, and the
    # run south inside that cap costs another 1 per lane, so the far row reads
    # ZERO and its dispensers never fire. Two boosts are needed.
    #
    # First, refill the spine immediately before each cap, so every cap lane is
    # fed at full strength rather than at whatever survived the trip.
    for cap_x in caps[1:-1]:
        reg[cap_x - 1, BUS_Y, honey_bus_z] = repeater

    # Second, boost partway down each cap lane, because a tall grid's southward
    # run is longer than 15. A repeater can only be placed where it AND the
    # block feeding it are both at bus level -- at a plant lane the wire dips a
    # level to sit on the dispenser, so neither that lane nor the one after it
    # can host one.
    # A repeater needs bus-level wire BEHIND it to read and bus-level wire IN
    # FRONT to drive: it outputs straight ahead and, unlike dust, will not step
    # down a level. One short of a dip it fires into the air gap above the
    # dispenser and that whole row goes dead -- measured, it cost every cap its
    # last row. So z-1, z and z+1 must all be clear of the dips.
    for cap_x in caps[:-1]:
        since = 0
        for z in range(honey_bus_z + 1, D - 1):
            since += 1
            if (since >= 8
                    and z not in plant_lanes
                    and (z - 1) not in plant_lanes
                    and (z + 1) not in plant_lanes):
                reg[cap_x, BUS_Y, z] = repeater_south
                since = 0

    # The button, on the outside north face of the west cap. It backs onto a
    # solid block rather than the wire, because a button cannot attach to dust;
    # that block is strongly powered and passes the signal into the line.
    reg[caps[0], BUS_Y, 1] = stone
    reg[caps[0], BUS_Y, 0] = wbutton

    if add_sign:
        # On top of the west cap, which is solid all the way up, so the sign
        # has something to stand on.
        sign(reg, 0, CONTAIN_Y + 1, 0,
             ["Bamboo Grid", VERSION, f"{cols}x{rows} mods",
              f"{cols * rows * columns} cols"])

    meta = dict(rows=rows, cols=cols, columns=columns, W=W, H=H, D=D,
                ctrl_x=ctrl_x, BUS_Y=CUT_Y + 3, cap_fill=cap_fill,
                nonstick=nonstick,
                CUT_Y=CUT_Y, WATER_Y=WATER_Y, TOP_Y=TOP_Y, CONTAIN_Y=CONTAIN_Y,
                X_PITCH=X_PITCH, caps=caps, drops=drops, rowinfo=rowinfo,
                stall_zone=list(stall_zone))
    return reg, meta


if __name__ == "__main__":
    import sys as _s
    rows = int(_s.argv[1]) if len(_s.argv) > 1 else 5
    cols = int(_s.argv[2]) if len(_s.argv) > 2 else 5
    reg, m = build_grid(rows=rows, cols=cols)
    total = rows * cols * m["columns"]
    save(reg, f"bamboo-grid-{cols}x{rows}",
         f"Bamboo Grid {cols}x{rows} {VERSION}",
         f"{total} planted columns in {m['W']}x{m['D']}; "
         f"{rows} firing lines, {cols} collection trenches.")
