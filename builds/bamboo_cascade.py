"""Bamboo cascade -- one chamber, one staircase, every step a crop row.

This follows the architecture of the user's own Terrace-v1 rather than the
tiered thing that preceded it. Read as a slice along the chamber, v1 is not a
stack of troughs at all: it is a single diagonal staircase whose treads are the
knives. Close the knives and the diagonal becomes an unbroken floor; pour water
in at the top and it falls one step at a time to the bottom.

    1. the knives close   pistons extend: the crop is cut AND the floor is made
    2. water in at the top   one row of dispensers, at the head of the staircase
    3. it only ever runs downhill, sweeping the crop ahead of it
    4. a row of hoppers at the foot of a tall wall takes everything
    5. the dispensers take the water back, the knives open, the crop regrows

MEASURED, because every previous cascade number here said this could not work:
water running ALONG a trough and spilling into the next tier managed 6.2% at two
tiers and swung 24%-96% at three. A staircase is a different regime -- falling
water restores its own spread when it lands, so the current renews at every
step. On a six-step staircase every tread ran wet and every seeded item reached
the bottom lane. See experiments/exp29_cascade_stairs.py.

WHY EVERY LANE CARRIES A CROP. The obsidian steps in v1 were not there for the
water, they were there so the retracted knives had somewhere to PARK -- a parked
knife fills a lane for the whole growth phase, and a lane with a knife in it
cannot also grow bamboo. That is what holds the terrace to one crop row in two.

Dropping FOUR blocks per step instead of one hides the park slot inside the
riser, under the next lane's soil, where nothing else wants the space:

    offset from this lane's tread          what lives there
       0    honey/wool blade               the tread, and the knife
      -1    bamboo stub
      -2    dirt
      -3    obsidian                       seals the riser
      -4    PARK -- the lane below's knife, while it is growing
      -5    obsidian                       seals under the park
      -6    stone
      -7    redstone dust                  firing bus, two lanes below's knife
      -8    obsidian + sticky piston           "

Every lane is identical and every lane grows bamboo: one crop row per lane
rather than one in two. Four is the smallest drop that works -- at three the
park slot lands directly under the soil, and honey drags every movable block it
touches, so the knife would carry the farm's dirt away with it. The obsidian at
-3 and -5 is not decoration: honey cannot move an immovable block, and the
piston fires anyway rather than jamming.

WIRING. The piston sits INSIDE its own bus -- a line of obsidian at the piston's
level with dust on top of it. Measured against three alternatives in
experiments/exp30_piston_in_bus.py; all four fire, and this one is the only one
that fits under the soil. One redstone torch tower carries a single lever up the
whole staircase; the rows are four blocks apart and each torch inverts, so every
tap is an even number of torches from the lever and they all fire in phase.
"""
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcschem import AIR, block, container, region, save, sign  # noqa: E402

VERSION = "cascade-v0.1"

DROP = 4            # blocks of fall per step; 3 puts the park under the soil
SEG = 8             # columns per blade segment: wool end, 6 honey, wool end
SEGL = 7            # columns a source pushes items before the bed steps down
PER_HOPPER = 118    # plants one hopper can take in a single harvest
HEADROOM = 11       # air above the top tread, for a full-height plant


def plan_stream(bx, width, nhop):
    """Feed columns, sump spans and hopper columns for the collection trough.

    Water flows only toward a drop within ~5 columns and spreads evenly only
    beyond that, so an interior feed whose two sumps sit at DIFFERENT distances
    -- 5 one way, 6 the other -- pushes everything to the nearer one and leaves
    the other leg of the trough permanently dry. Even spacing does not give
    equal distances once the positions are rounded to whole blocks, so the
    arrangement is searched for rather than computed.

    A feed reaches 7 columns (level 7 is the last), which is why a sump lip more
    than 6 away is out of reach and rejected.
    """
    REACH = 6                      # furthest a feed can put water on a sump lip
    SEARCH = 5                     # the hole-search radius, in columns
    ends = (bx, bx + width - 1)

    def evaluate(feeds):
        sumps, hops = [], []
        for a, b in zip(feeds, feeds[1:]):
            lo, hi = a + REACH, b - REACH
            if lo > hi:                        # the two feeds' reaches overlap
                # two wide, never one: the crop settles on the two columns
                # where the opposing flows cancel, and both need a hopper
                lo = (a + b) // 2
                hi = lo + 1
            if lo - a > REACH or b - hi > REACH:
                return None                    # a leg out of reach: it stays dry
            sumps.append((lo, hi))
            c = (lo + hi) // 2                 # the centre pair of this sump
            hops.append(min(c, hi - 1))
        for i in range(1, len(feeds) - 1):
            dl = feeds[i] - sumps[i - 1][1]
            dr = sumps[i][0] - feeds[i]
            if dl != dr and not (dl > SEARCH and dr > SEARCH):
                return None                    # this feed would drive one leg
        return sumps, hops

    best = None
    interior = range(bx + REACH, bx + width - REACH)
    for cand in itertools.combinations(interior, nhop - 1):
        feeds = [ends[0], *cand, ends[1]]
        got = evaluate(feeds)
        if got is None:
            continue
        gaps = [b - a for a, b in zip(feeds, feeds[1:])]
        score = (max(gaps) - min(gaps), abs(sum(gaps) / len(gaps) - 12))
        if best is None or score < best[0]:
            best = (score, feeds, *got)
    if best is None:
        raise ValueError(
            f"no feed spacing for a {width}-wide trough with {nhop} hoppers "
            "leaves every leg wet; use a different hopper count")
    return best[1], best[2], best[3]


def layout(rows, cols, bx=3):
    """Every coordinate the build needs, in one place so it can be checked."""
    # x of the first blade column. 3 is the tight default; 7 puts a 24-wide
    # crop at exactly W=32, a two-chunk footprint that tiles on chunk lines.
    width = cols * SEG
    W = bx + width + 1                      # + east wall
    D = rows + 6                            # wall, feed, trough, lanes, wall
    base = 10                               # tread of lane 0
    fan_h = (width + 1) // 2               # steps to fan to full width
    # Nothing sits above the dust row that fires the dispenser, so the build
    # stops there. It used to run to HEADROOM + 4 above the fan, which was
    # eleven levels of side column and back wall holding nothing up.
    top_y = base + DROP * rows + fan_h + 2      # the dispenser's dust row
    H = top_y + 1

    def lane_z(L):
        return 3 + L                        # lane L sits at z = 3 + L

    def floor_y(L):
        return base + DROP * L

    piston_xs = [bx + m * SEG + 1 for m in range(cols)]
    fan_x = bx + width // 2                # the one dispenser, centred
    return dict(bx=bx, width=width, W=W, D=D, H=H, base=base,
                # where the one lever sits, published so no probe has to
                # re-derive it: firing a block too high reads exactly like
                # a farm whose pistons never move
                tower_y0=base - 7, tower_zb=3,
                lane_z=lane_z, floor_y=floor_y, piston_xs=piston_xs,
                rows=rows, cols=cols,
                hopper_z=2, feed_z=1, wall_z=0, tower_z=2,
                fan_h=fan_h, fan_x=fan_x, top_y=top_y)


def build_region(rows=6, cols=3, add_sign=True,
                 hard="white_glazed_terracotta", fill="stone", lean=True, disp_every=3,
                 fan=True, stream=True, bx=3):
    """`hard` is the block honey cannot drag; `fill` is everything else.

    `fill` must be a FULL SOLID block that does not fall -- stone,
    cobblestone, dirt, deepslate, blackstone and planks all work. Sand,
    gravel and concrete powder FALL. Slabs, glass and leaves are not full
    blocks, and the tower and the dust supports have to conduct.

    `fan` feeds the header from ONE dispenser through a stepped pyramid that
    widens by a column each side per step down, so the water arrives at the
    header tread already spread across the full width. Feeding the header in
    separate columns instead -- even one column in three -- sends the water
    straight down those columns and misses the crop between them.

    `lean` drops every fill block sealed inside the structure, leaving a
    one-block shell. Solid fill is over half the build and hides what the
    machine is doing.

    `hard` -- measured interchangeable:
    obsidian, furnace (8 cobble), barrel (6 planks + 2 slabs), dropper,
    crying obsidian -- all refuse the drag and still conduct, so any of
    them works in the bus course too. Chest and enchanting table refuse
    the drag but do NOT conduct, so they cannot carry the firing line."""
    m = layout(rows, cols, bx=bx)
    W, H, D = m["W"], m["H"], m["D"]
    bx, width = m["bx"], m["width"]
    lane_z, floor_y = m["lane_z"], m["floor_y"]
    reg = region(W, H, D)

    stone = block(fill)
    obs = block(hard)
    soil = block("dirt")
    shoot = block("bamboo", age="0", leaves="none", stage="0")
    honey = block("honey_block")
    wool = block("orange_wool")
    dust = block("redstone_wire", east="side", west="side",
                 north="side", south="side", power="0")
    lever = block("lever", face="floor", facing="north", powered="false")
    # a repeater's `facing` names its INPUT side, so a line running east faces west
    rep_e = block("repeater", facing="west", delay="1",
                  locked="false", powered="false")
    hopper_d = block("hopper", facing="down", enabled="true")
    chest = block("chest", facing="north", type="single")
    disp_n = block("dispenser", facing="north", triggered="false")
    water = block("water", level="0")           # level 0 is a SOURCE

    for x in range(W):
        for y in range(H):
            for z in range(D):
                reg[x, y, z] = AIR

    top_lane = rows + 1                     # lanes 0..rows-1 crop, rows header,
    #                                          rows+1 dispensers and machinery

    # ---- the lanes ---------------------------------------------------------
    for L in range(top_lane + 1):
        z, fy = lane_z(L), floor_y(L)
        crop = L < rows

        for x in range(bx, bx + width):
            seg_first = bx + ((x - bx) // SEG) * SEG
            end = x in (seg_first, seg_first + SEG - 1)

            if crop:
                reg[x, fy - 2, z] = soil
                reg[x, fy - 1, z] = shoot
                # the tread itself is the knife, and it is shipped PARKED --
                # one lane south and DROP blocks down. Flip the lever and the
                # staircase closes.
            elif L == rows:
                # Just the tread. The two courses under it used to be filled to
                # mirror the crop lanes' soil and shoot, but nothing rests on
                # them: the tread is solid and the parked blade below already
                # has its furnace lid.
                reg[x, fy, z] = obs         # header tread: water lands here

            # The seals exist only to cap a PARKED blade -- above it so honey
            # cannot drag the riser away, below it so honey has something
            # immovable to sit on. Where no blade parks there is nothing to
            # seal, and placing them anyway blocks the header shelf's water.
            if 0 <= L - 1 < rows:
                reg[x, fy - 3, z] = obs      # riser seal / lid over the park
                reg[x, fy - 4, z] = wool if end else honey
                reg[x, fy - 5, z] = obs      # floor under the park

            # Firing bus for the knife two lanes below. The dust rides on a
            # solid course ABOVE the pistons rather than on the pistons
            # themselves: dust laid directly on a piston is DESTROYED the
            # moment that piston fires, which cuts the line and leaves every
            # segment past the first dead. Measured -- the first piston
            # extended, the dust above it became air, and the rest of the bus
            # read power 0 all the way to the end.
            if L - 2 >= 0 and L - 2 < rows:
                # The bus runs at the PISTONS' OWN level + 1, on the course the
                # pistons sit in, and humps up over each piston rather than
                # laying dust on it (dust on a piston is destroyed the moment
                # it fires). That puts powered blocks directly beside every
                # piston instead of only above it.
                #
                # Two levels up, the farm extended fine and then would not let
                # go: the bus read [0,0,0,0] with seven of eight pistons still
                # extended, and poking any neighbour retracted all eight at
                # once -- a missed block update, not a stuck piston.
                reg[x, fy - 8, z] = obs      # the pistons sit in this course
                reg[x, fy - 7, z] = dust     # the bus, beside each piston
            else:
                reg[x, fy - 8, z] = stone
                reg[x, fy - 7, z] = stone

            for y in range(0, fy - 8):
                reg[x, y, z] = stone

        # the pistons, embedded in that bus
        if L - 2 >= 0 and L - 2 < rows:
            for px in m["piston_xs"]:
                reg[px, fy - 8, z] = block("sticky_piston", facing="north",
                                           extended="false")
                # carry the line over the piston: dust steps up and back down,
                # which needs the blocks above its neighbours left open
                reg[px, fy - 7, z] = obs
                reg[px, fy - 6, z] = dust
                for dx in (-1, 1):
                    if bx <= px + dx < bx + width:
                        reg[px + dx, fy - 6, z] = AIR

    # ---- repeaters on every bus line ---------------------------------------
    # Dust carries 15 blocks. Without these the segments past the first 15
    # simply never fire, and the schematic looks perfectly continuous.
    for L in range(2, top_lane + 1):
        r = L - 2
        if not (0 <= r < rows):
            continue
        z, y = lane_z(L), floor_y(L) - 7
        x = bx + 12
        while x < bx + width:
            if x not in m["piston_xs"]:
                reg[x, y, z] = rep_e
                x += 14
            else:
                x += 1

    # ---- collection ---------------------------------------------------------
    hz, fz, fy0 = m["hopper_z"], m["feed_z"], floor_y(0)
    if stream:
        # One hopper per PER_HOPPER plants, each with its OWN drop point:
        # hoppers banked together under a single current do not share a burst,
        # so a row of them at one outlet would collect no more than one does.
        nhop = max(1, -(-(rows * width) // PER_HOPPER))
        bed = fy0 - 3                          # water sits one above the bed
        wat = bed + 1
        sump = bed - 1                         # the hopper, one lower still

        # A feed reaches about six columns along the trough, so they go at the
        # two ends and at each zone boundary, with a hopper at every midpoint.
        # A feed's last column is level 7, six along from the one it faces, so
        # each sump starts there and the water falls in instead of stopping
        # short. The spacing is searched, not computed: see plan_stream.
        # capacity sets the floor; geometry may need more zones than that
        for n in range(nhop, nhop + 6):
            try:
                feeds, spans, hops = plan_stream(bx, width, n)
                nhop = n
                break
            except ValueError:
                continue
        else:
            raise ValueError(
                f"cannot plumb a {width}-wide trough at any hopper count")
        sumps = {x for lo, hi in spans for x in range(lo, hi + 1)}

        # No pit. The crop settles ON the sump floor, at the two centre
        # columns where the opposing flows cancel -- measured at 371 and 320
        # items against 5 and 2 on the columns either side. A pit one block
        # deeper put the hopper below all of it and collected nothing.
        pit = sump
        pits = {x for c in hops for x in (c, c + 1)}
        for x in range(bx, bx + width):
            b = sump if x in sumps else bed
            for y in range(0, b + 1):
                reg[x, y, hz] = stone          # the bed and all beneath it
            for y in range(b + 1, fy0 + 1):
                reg[x, y, hz] = AIR            # the trough, open so crop falls in
            # The feed wall: solid beside the water so the stream cannot
            # spread into it, and carried ABOVE the level the crop travels at.
            # Stopping it at fy0 left a ledge at fy0+1 -- items swept one block
            # too far north landed on it, dry and out of reach of any current,
            # and 521 of 576 died there.
            for y in range(pit - 1, floor_y(rows) + HEADROOM):
                reg[x, y, fz] = stone
            # and the trough's back, or it drains into the void under lane 0
            # and reaches that lane's bus
            for y in range(pit - 1, bed + 1):
                reg[x, y, lane_z(0)] = stone

        # a hopper on BOTH columns the flows converge on
        for c in sorted(pits):
            reg[c, sump, hz] = hopper_d
            reg[c, sump - 1, hz] = chest
        for fx in feeds:
            reg[fx, wat, fz] = water           # level 0 -- a source
        m["hoppers"] = [(c, sump, hz) for c in sorted(pits)]
        m["chests"] = [(c, sump - 1, hz) for c in sorted(pits)]
        m["feeds"] = [(fx, wat, fz) for fx in feeds]

    else:
        for x in range(bx, bx + width):
            reg[x, fy0 - 2, hz] = chest
            reg[x, fy0 - 1, hz] = hopper_d
            for y in range(0, fy0 - 2):
                reg[x, y, hz] = stone
    # the tall wall the water stops against
    for x in range(bx, bx + width):
        for y in range(0, floor_y(rows) + HEADROOM):
            reg[x, y, m["wall_z"]] = stone

    # ---- side walls --------------------------------------------------------
    for z in range(0, D):
        for y in range(0, m["top_y"] + 1):
            for x in (bx - 1, bx + width):
                if reg[x, y, z].id == "minecraft:air":
                    reg[x, y, z] = stone

    # ---- the fan: one dispenser, spread by a stepped pyramid ---------------
    dz, dfy = lane_z(top_lane), floor_y(rows)
    hz = lane_z(rows)
    fan_h, fan_x = m["fan_h"], m["fan_x"]

    # the pyramid, in the header lane: full width at the tread, one block
    # narrower each side per step up, to a single block at the apex
    for j in range(1, fan_h + 1):
        half = max(0, (width - 2 * j) // 2)
        lo = max(bx, fan_x - half)
        hi = min(bx + width - 1, fan_x + half)
        for x in range(lo, hi + 1):
            reg[x, dfy + j, hz] = stone

    # the dispenser sits one above the apex, in the lane behind, firing north
    # onto it; the rest of that lane is the wall that stops the water running
    # backwards off the pyramid
    for j in range(1, fan_h + 2):
        for x in range(bx, bx + width):
            reg[x, dfy + j, dz] = stone
    for x in range(bx, bx + width):
        reg[x, dfy + 1, dz] = stone
    container(reg, fan_x, dfy + fan_h + 1, dz, disp_n,
              [(0, "water_bucket", 1)])

    # its button, and the line to it
    reg[bx - 1, dfy + fan_h + 2, dz] = lever
    for x in range(bx, bx + width):
        reg[x, dfy + fan_h + 2, dz] = dust
    x = bx + 12
    while x < bx + width:
        # never on the dispenser: dust powers the block below it, a repeater
        # does not, so a repeater here leaves the dispenser dead
        rx = x + 1 if x == fan_x else x
        if rx < bx + width:
            reg[rx, dfy + fan_h + 2, dz] = rep_e
        x += 14

    # ---- one lever for every knife: a redstone torch tower -----------------
    # Each torch inverts, so a tap is only in phase with the lever an EVEN
    # number of torches up. The bus lines are DROP apart and DROP is even, so
    # every row taps in phase from a single lever.
    #
    # The tower stands at x=0 and its feeds run at x=1, both OUTSIDE the
    # chamber's west wall. That matters: row r's feed sits at exactly lane r's
    # waterline, so running it through the wall would open the chamber at the
    # water level and drain the lane it was meant to fire.
    tz, tx = m["tower_z"], 0
    # The taps must sit an EVEN number of torches above the base or they fire
    # inverted, so y0 is chosen from where the bus lines ended up.
    y0 = m["tower_y0"]
    steps = DROP * (rows - 1) + 9
    # The TAP blocks sit on the southern column and the torches on the
    # northern one. The other way round put a lit torch directly alongside
    # every feed line, and a lit torch powers adjacent dust -- so the farm sat
    # switched ON at rest, knives already extended, with the lever untouched.
    # Row 3 was the tell: it read correctly OFF, because its torch is the one
    # the ladder omits at the top.
    for k in range(steps):
        y = y0 + k
        reg[tx, y, tz + ((k + 1) % 2)] = stone
        if k + 1 < steps:
            # Shipped UNLIT. A torch placed lit briefly powers the block
            # above it before it re-evaluates, and at the top of the ladder
            # that pulse reaches a bus for about a tick. A sticky piston given
            # a one-tick pulse extends and retracts but LEAVES THE BLOCK
            # BEHIND -- which stranded one knife of the top row on its tread
            # every single build, and starved every column below it of water.
            # The game lights the torch on the first update.
            reg[tx, y, tz + (k % 2)] = block(
                "redstone_wall_torch",
                facing="north" if k % 2 == 0 else "south", lit="false")
    for y in range(0, y0):
        reg[tx, y, tz] = stone
        reg[tx, y, tz + 1] = stone
        reg[tx, y, tz + 2] = stone
    # A WALL lever on the base block. Putting it on top landed it exactly where
    # the tower's second torch goes, silently deleting that torch -- which both
    # breaks the ladder and flips the polarity of everything above it.
    reg[tx, y0, tz + 2] = block("lever", face="wall", facing="south",
                                powered="false")

    # feeds: tap the tower every DROP blocks, run north-to-south at x=1, and
    # cross the wall only at the bus lane, which is eight blocks under the soil
    for r in range(rows):
        y = floor_y(r + 2) - 7
        z_bus = lane_z(r + 2)
        for z in range(tz + 1, z_bus + 1):
            reg[1, y - 1, z] = stone
            reg[1, y, z] = dust
        # ... then east along the bus lane to the wall. With bx=3 this is empty
        # and the feed stepped straight onto the repeater; any wider margin and
        # the signal has a gap to cross that it silently will not.
        for x in range(2, bx - 1):
            reg[x, y - 1, z_bus] = stone
            reg[x, y, z_bus] = dust
        # A repeater where the feed crosses the wall. Without it the bus
        # starts at whatever the feed had left -- measured 11, 10, 9 and 8 for
        # the four rows, because each feed runs a different distance in z --
        # and the far half of every row is dead before the first repeater on
        # the line is even reached. With it, every bus starts at 15.
        reg[bx - 1, y - 1, z_bus] = stone
        reg[bx - 1, y, z_bus] = rep_e

    # south wall, so the chamber is closed
    for x in range(bx - 1, bx + width + 1):
        for y in range(0, m["top_y"] + 1):
            if reg[x, y, D - 1].id == "minecraft:air":
                reg[x, y, D - 1] = stone

    # ---- demote every immovable block honey cannot reach ------------------
    # Honey drags face-adjacent MOVABLE blocks, so a block only has to resist
    # that if it touches a honey blade in one of the two states a blade is ever
    # in: parked, or extended onto its tread. Wool ends grip nothing, so their
    # neighbours are deliberately not counted.
    honey_cells, blade_cells = set(), set()
    for r in range(rows):
        for x in range(bx, bx + width):
            parked = (x, floor_y(r), lane_z(r + 1))
            here = [parked, (x, floor_y(r), lane_z(r))]
            blade_cells.update(here)
            if reg[parked].id == "minecraft:honey_block":
                honey_cells.update(here)

    must_hold = set()
    for (x, y, z) in honey_cells:
        for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z),
                  (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)):
            if n not in blade_cells:
                must_hold.add(n)

    hard_id = f"minecraft:{hard}" if ":" not in hard else hard
    for x in range(W):
        for y in range(H):
            for z in range(D):
                if reg[x, y, z].id == hard_id and (x, y, z) not in must_hold:
                    reg[x, y, z] = stone

    # ---- strip the fill ----------------------------------------------------
    # A block with six solid neighbours holds no water, supports no dust and
    # cannot be reached by honey, so it is doing nothing but hiding the design.
    # Only `fill` is eligible: never the immovable blocks, the soil, the
    # treads, or anything carrying redstone.
    if lean:
        NONSOLID = {"minecraft:air", "minecraft:redstone_wire",
                    "minecraft:repeater", "minecraft:lever", "minecraft:water",
                    "minecraft:redstone_wall_torch", "minecraft:bamboo",
                    "minecraft:hopper", "minecraft:chest",
                    "minecraft:sticky_piston", "minecraft:oak_sign"}
        fill_id = stone.id

        def solid(x, y, z):
            if not (0 <= x < W and 0 <= y < H and 0 <= z < D):
                return True          # outside is solid, so the outer floor goes
            return reg[x, y, z].id not in NONSOLID

        doomed = [
            (x, y, z)
            for x in range(W) for y in range(H) for z in range(D)
            if reg[x, y, z].id == fill_id
            and all(solid(x + dx, y + dy, z + dz) for dx, dy, dz in
                    ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                     (0, -1, 0), (0, 0, 1), (0, 0, -1)))
        ]
        for c in doomed:
            reg[c] = AIR

    if add_sign:
        reg[0, m["base"] - 1, 1] = stone
        # rotation=8 faces NORTH -- the open side. The default, 0, faces south
        # straight into the stone this sign stands beside.
        text = ["Bamboo Cascade", VERSION,
                f"{rows} rows x {cols * SEG}", "1 lever, 1 button"]
        sign(reg, 0, m["base"], 1, text, rotation=8, back=text)
    return reg, m


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=6)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    reg, m = build_region(rows=a.rows, cols=a.cols)
    name = a.out or f"bamboo-cascade-{a.rows}x{a.cols * SEG}"
    save(reg, name, "Bamboo Cascade",
         f"{VERSION} -- {a.rows} crop rows, {a.cols * SEG} wide")
    print(f"{name}: {m['W']} x {m['H']} x {m['D']}  "
          f"({a.rows * a.cols * SEG} plants, "
          f"{len(m.get('hoppers', [])) or a.cols * SEG} hoppers)")
