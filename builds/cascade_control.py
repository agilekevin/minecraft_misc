"""One button drives the whole harvest.

    press          knives extend, the staircase closes, the crop is cut,
                   and the water goes out on the SAME signal
    +37s           water taken back
    +127s          knives park, the crop regrows

Water cascades far more slowly than a piston fires, so the knives and the water
can share one start signal -- there is no need to delay the water behind the
blades. That removes a whole timing tap. What is left needs exactly two events:
take the water back, and much later park the knives.

Timed by ONE hopper pair. A holds 320 items and drains into B at a measured
0.393 s/item, so it empties in about 127 seconds, and a comparator on A steps 15
down to 0 on the way. One tap partway down takes the water back; the hopper
running dry parks the knives. The 90-second gap between them is what lets the
water drain completely before the staircase opens -- draining is a function of
HEIGHT, and 90s covers the tallest build here (measured: ~30s at 4 rows, over
52s at 8 rows).

One bit of state says whether a harvest is running, because the hopper alone
cannot: draining and refilling look identical from outside.

    idle     Q1 lit  -> A locked, B unlocked  -> B refills A, the timer resets
    running  Q2 lit  -> B locked, A unlocked  -> A drains, the cycle is timed

HOPPER A STANDS ON THE IDLE TORCH, so the latch locks it with no wire at all.
Measured: a lit torch directly beneath a hopper holds it shut (enabled=false,
320 items unmoved), and it releases the instant the torch goes out. The wire
this replaces was the one thing that broke every earlier version -- a comparator
STRONGLY POWERS THE BLOCK IT FACES, and a strongly powered block powers adjacent
dust, so the "A is empty" detector was feeding A's lock wire and holding the
hopper shut no matter what the latch did. No wire, no hijack.

TWO dispensers, not one. A dispenser fires on a RISING edge and the taps are
levels that stay high once crossed, so one dispenser would fire once and never
again. The running signal drives a dispenser holding a WATER bucket; the
water-back tap drives one holding an EMPTY bucket, aimed at the same cell.

Conventions, every one of which failed silently when guessed:
  * a comparator reads a container from ANY side; `facing` points at its INPUT
  * a comparator strongly powers the block it FACES -- keep dust away from it
  * a wall torch's support is the block OPPOSITE its facing
  * dust cannot rest on dust, a torch or a hopper -- run check_wiring
  * a dust line cannot climb inside one column; it steps sideways as it rises
  * dust connects DIAGONALLY to a wire one level down unless a solid block sits
    above the lower wire, so lines that merely pass near each other can merge
  * a wire dies after 15 blocks; the latch's feedback loop must stay under that
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcschem import block, container                           # noqa: E402

STONE = block("stone")
DUST = block("redstone_wire")
TIMER_ITEMS = 320
TAP_BACK = 10                     # comparator level -> water back at ~37s


def _torch(f):
    return block("redstone_wall_torch", facing=f, lit="false")


def _cmp(f):
    return block("comparator", facing=f, mode="compare", powered="false")


def _rep(f):
    return block("repeater", facing=f, delay="1", locked="false",
                 powered="false")


def sequencer(reg, ox, oy, oz):
    """Stamp the control circuit; return the cells the farm wires into."""
    seen = {}

    def put(x, y, z, b):
        was = seen.get((x, y, z))
        if was is not None and was != b.id:
            raise ValueError(
                f"sequencer collision at local {(x, y, z)}: {was} then {b.id}")
        seen[(x, y, z)] = b.id
        reg[ox + x, oy + y, oz + z] = b

    def wire(cells):
        for (x, y, z) in cells:
            put(x, y, z, DUST)
            put(x, y - 1, z, STONE)

    def stair(cells):
        """Each wire one higher than the last, on its own block."""
        for (x, y, z) in cells:
            put(x, y - 1, z, STONE)
            put(x, y, z, DUST)

    # ---- the latch --------------------------------------------------------
    for gx in (0, 6):
        put(gx, -1, 0, STONE)
        put(gx, 0, 0, STONE)
        put(gx, 1, 0, DUST)                        # the gate's input
    put(1, 0, 0, _torch("east"))                   # Q1: lit when IDLE
    put(7, 0, 0, _torch("east"))                   # Q2: lit when RUNNING
    wire([(2, 0, 0), (3, 0, 0), (4, 0, 0), (5, 0, 0)])   # Q1 -> gate 2

    # Q2 -> gate 1. It has to go round the timer, and a wire dies after 15
    # blocks, so it carries a repeater on the way.
    wire([(8, 0, z) for z in range(6)])
    wire([(x, 0, 5) for x in range(7, 4, -1)])
    put(4, -1, 5, STONE)
    put(4, 0, 5, _rep("east"))
    wire([(x, 0, 5) for x in range(3, -1, -1)])
    wire([(0, 0, z) for z in (4, 3, 2, 1)])        # steps up into gate 1

    # ---- the timer --------------------------------------------------------
    # A sits ON the idle torch: lit torch = locked hopper, no wire needed.
    container(reg, ox + 1, oy + 1, oz,
              block("hopper", facing="east", enabled="true"),
              [(s, "cobblestone", 64) for s in range(5)])
    seen[(1, 1, 0)] = "minecraft:hopper"
    put(2, 1, 0, block("hopper", facing="west", enabled="true"))   # B -> A
    put(2, 2, 0, STONE)                            # B's lock block, above B
    put(2, 3, 0, DUST)                             # powered by Q2 -> B locked

    # Q2 climbs north of everything to reach B's lock
    # Keep this branch AWAY from gate 2's own block at (6,0,0). Routed through
    # (6,0,-1) it ran right alongside it, so Q2 powered the block its own torch
    # is attached to and switched itself off after a couple of seconds.
    wire([(7, 0, -1), (7, 0, -2), (6, 0, -2)])
    stair([(5, 1, -2), (4, 2, -2), (3, 3, -2)])
    wire([(2, 3, -2), (2, 3, -1)])                 # meets B's lock dust

    # ---- water back: one tap, reading A from the north --------------------
    put(1, 0, -1, STONE)
    put(1, 1, -1, _cmp("south"))
    n = TAP_BACK + 1                               # dies as the level hits 10
    wire([(1, 1, -1 - k) for k in range(1, n + 1)])
    put(1, 1, -2 - n, STONE)
    put(1, 2, -2 - n, DUST)
    put(1, 1, -3 - n, _torch("north"))
    water_back = (1, 1, -3 - n)

    # ---- "A is empty" -> RESET, on A's other side -------------------------
    # Its target block is kept clear of every wire: this comparator is what
    # hijacked A's lock in the previous version.
    put(1, 0, 1, STONE)
    put(1, 1, 1, _cmp("north"))                    # reads A, to its north
    put(1, 1, 2, STONE)                            # strongly powered by it
    put(1, 1, 3, _torch("south"))                  # lit only when A runs dry
    wire([(x, 1, 3) for x in range(2, 7)])
    # RESET enters through a REPEATER, which passes one way only. Wired as bare
    # dust it does not deliver RESET at all: gate 2's own input node feeds
    # BACKWARDS into it (measured -- the line read 10 with the torch dark),
    # which extends the latch's internal node and stops it holding.
    wire([(6, 1, 2)])
    put(6, 0, 1, STONE)
    put(6, 1, 1, _rep("south"))                    # -> gate 2's input = RESET

    # ---- the button -------------------------------------------------------
    put(-1, 1, 0, STONE)
    put(-2, 1, 0, block("stone_button", face="wall", facing="west",
                        powered="false"))
    return {"button": (-2, 1, 0),
            "knives": (7, 0, 0),        # Q2: high for the whole harvest
            "water_out": (7, 0, 0),     # the SAME signal -- water needs no delay
            "water_back": water_back,
            "hopper_a": (1, 1, 0), "hopper_b": (2, 1, 0),
            "idle_torch": (1, 0, 0)}
