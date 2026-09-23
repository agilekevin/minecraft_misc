"""The sequencer on its own, with signs saying what each wire is for.

Just the control circuit -- no farm, no crop, no walls. Every output carries a
sign naming what it connects to in the real build, so the whole thing can be
read at a glance instead of traced through code.

    PRESS TO HARVEST      the button
    TO HARVEST BLADE      goes high for the whole cycle; drives the piston tower
    TO WATER-OUT          fires about 10s in; dispenser with a WATER bucket
    TO WATER-BACK         fires about 37s in; dispenser with an EMPTY bucket
    TIMER                 hopper A; fill it with 5 stacks of anything
    KNOWN FAULT           where it is currently broken

Status, honestly: the latch holds, the button starts it, and the three taps fire
at the right times when tested on their own. Assembled, the timer does not start
-- hopper A's lock wire reads 12 when the idle torch is DARK, so something is
feeding that wire other than the torch it is supposed to come from. One cell of
that run reads 15, a source-level value, which means power enters partway along
rather than flowing from the start.

Two things to fill in by hand after pasting, because Litematica drops container
contents: five stacks into the timer hopper, and the buckets into whichever
dispensers you wire the two water outputs to.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcschem import AIR, block, region, save, sign              # noqa: E402
from cascade_control import sequencer                           # noqa: E402

STONE = block("stone")

# room for the circuit plus a sign beside every port
W, H, D = 30, 8, 32
OX, OY, OZ = 16, 2, 24

LABELS = [
    # (x, y, z, rotation, lines) -- positions are local to the circuit
    (-1, 1, 2, 0, ["PRESS TO HARVEST", "one press runs", "the whole cycle",
                   "~127 s"]),
    (9, 1, 0, 0, ["TO BLADE + WATER", "this ONE signal does", "both: knives out",
                  "and water out"]),
    (3, 1, -14, 0, ["TO WATER-BACK", "dispenser, EMPTY", "bucket, same cell",
                    "fires ~37 s in"]),
    (3, 1, 1, 0, ["TIMER", "fill hopper with", "5 stacks of any", "item = 127 s"]),
    (7, 1, 3, 0, ["KNOWN FAULT", "latch will not hold", "cycle stops after", "~3 seconds"]),
]


def build_region():
    reg = region(W, H, D)
    for x in range(W):
        for y in range(H):
            for z in range(D):
                reg[x, y, z] = AIR
    ports = sequencer(reg, OX, OY, OZ)

    for (lx, ly, lz, rot, lines) in LABELS:
        px, py, pz = OX + lx, OY + ly, OZ + lz
        if reg[px, py - 1, pz].id == "minecraft:air":
            reg[px, py - 1, pz] = STONE           # a post to stand the sign on
        sign(reg, px, py, pz, lines, rotation=rot, back=lines)
    return reg, ports


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments"))
    from check_wiring import check                              # noqa: E402

    reg, ports = build_region()
    bad = check(reg, "sequencer-only")
    n = sum(1 for x in range(W) for y in range(H) for z in range(D)
            if reg[x, y, z].id != "minecraft:air")
    print(f"  {W}x{H}x{D}, {n} non-air blocks")
    print("  ports (local to the circuit's own origin):")
    for k, v in ports.items():
        print(f"     {k:<12} {v}")
    save(reg, "cascade-sequencer-v1", "Cascade sequencer",
         "control circuit only, with labels; timer does not yet start")
