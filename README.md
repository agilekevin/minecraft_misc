# minecraft_misc

Minecraft builds authored as code. Each script in `builds/` writes a
`.litematic` file you paste (creative) or hand-build (survival) with
[Litematica](https://modrinth.com/mod/litematica). Generated schematics are in
`schematics/`, so you can use them without running anything.

Built for **Minecraft 1.21.8**, and aimed at a civ-style server: no flying
machines, chunk limits on hoppers and pistons, crops that grow slowly.

## Running a build

```bash
python3 -m venv venv && ./venv/bin/pip install litemapy
export MCBUILD_SCHEMATIC_DIR="/path/to/.minecraft/schematics"   # optional
./venv/bin/python builds/bamboo_cascade.py --rows 4 --cols 2
```

Without `MCBUILD_SCHEMATIC_DIR` the file lands in `schematics/` next to the
script. `save()` reads the file back before reporting success, because a corrupt
schematic saves happily and would otherwise only fail minutes later in game.

**The data version must match your Minecraft version** — 4440 for 1.21.8.
litemapy defaults to 2975 (1.18.2), which makes Litematica read every block
state as that version's.

## The bamboo cascade

`builds/bamboo_cascade.py` is the main build: a self-harvesting bamboo farm that
needs no flying machine. Read as a slice along the chamber it is one diagonal
staircase whose treads **are** the harvesting knives — sticky pistons pushing
honey blocks. Close them and the diagonal becomes an unbroken floor; pour water
in at the top and it falls one step at a time, washing the crop to the hoppers
at the foot.

Measured in game at three sizes: **93–96% of the crop banked**, from one
dispenser and one bucket.

Things that were expensive to learn, and are baked into the script:

- **A staircase cascade works; a trough cascade does not.** Falling water
  restores its spread when it lands, so the current renews at every step. Water
  running *along* troughs managed 6–24%.
- **Water reaches the full width from ONE dispenser** via a stepped pyramid that
  widens by a column each side per step down. Feeding separate columns instead —
  even one in three — sends the water straight down those columns and misses the
  crop between them.
- **Power each piston from its own course**, one level up and humped over the
  piston. Powering through a block from two levels up extends reliably and does
  **not** retract reliably; dust laid directly on a piston is destroyed when it
  fires.
- **Ship redstone torches unlit.** A torch placed lit briefly powers the block
  above it, and that one-tick pulse makes a sticky piston extend and retract but
  leave its block behind.
- **The immovable block is a choice.** `build_region(hard=..., fill=...)`:
  obsidian, furnace, barrel, dropper and glazed terracotta all refuse the honey
  drag; chest and enchanting table refuse it but do not conduct redstone, so they
  cannot carry a firing line. `fill` must be a full solid block that does not
  fall — sand and gravel do.
- **One hopper per ~118 plants**, each with its own sump, instead of a hopper
  row. It matters where hoppers are chunk-limited.

### The two shipped schematics

`bamboo-cascade-8x32-cobble.litematic` is exactly what `builds/bamboo_cascade.py
--rows 8 --cols 4` writes, with cobblestone as the fill.

`bamboo-cascade-4x16-cobble.litematic` has been **edited past what the script
produces**, for building by hand on a server:

- both controls at ground level — a lever for the knives, a second redstone
  torch ladder bringing the water lever's signal 31 blocks up — with signs
- the enclosing shell above the header, the back wall and a vestigial corner
  column removed (687 blocks, about 11 stacks of cobble)
- lowered so the collection chests sit on the bottom row
- cobblestone blade ends instead of orange wool

1,542 blocks: 1,050 cobblestone, 136 white glazed terracotta, 48 honey, 102
redstone dust, 48 torches, 10 repeaters, 8 sticky pistons. Regenerating it from
the script will **not** reproduce these edits.

## Slice mode: tiling a wide farm

A 128-wide farm is not one schematic. The design's period along X is 8 columns,
so `build_parts()` cuts a finished build into a repeating **module** and the
one-off end pieces, and you tile the module with Litematica's grid placement:

```bash
./venv/bin/python builds/bamboo_cascade.py --rows 8 --cols 16 --parts
```

| Piece | Tiles? | Why |
|---|---|---|
| `module` | **every 8 blocks in X** | blades, soil, riser seals, pistons, firing bus, south wall |
| `fan` | no | its height is half the width, so it is built once |
| `collection` | no | `plan_stream` *searches* for sump spacing; it is not periodic |
| `west` | no | the torch tower and the controls |
| `east` | no | the east wall |

Every piece comes back in the same coordinate frame, so they share one origin;
only the module repeats.

The cut is by **provenance, not geometry**: the builder tags each cell with the
stage that wrote it, so nothing is duplicated or kept in step by hand.
`verify_parts()` reassembles the pieces and diffs them against the monolith —
exact at 4x16, 6x24, 8x32 and 12x48, and `build_parts()` refuses outright if any
segment differs from the one it is about to ship.

The module carries one bus repeater per line at a fixed column, because the
monolith spaces them every 14 blocks, which never lines up with 8. That costs one
redstone tick per module, so the far end of a 16-module farm fires ~0.8 s after
the near end. The knives close before the water starts, so it does not matter.

**Tiling whole units is the cheaper option if you do not need one set of
controls.** Four 8x32 units cost 25.9 blocks per plant against 25.8 for one
128-wide farm — the fan, tower and collection are tiny next to the bulk — and
each unit is self-contained and independently measured.

## Building it in survival

The 4×16 in `schematics/bamboo-cascade-4x16-cobble.litematic` is trimmed for
hand-building: 1,542 blocks, mostly cobblestone, with both controls at ground
level behind signs (a lever for the knives, and the water). Only about 45 blocks
have a facing that matters — the pistons above all.

Litematica's **Easy Place** will do the rest, but on a server with anti-cheat,
aim at the face of a block that is already there: with no real block behind the
hologram cell, Litematica sends a click on an empty position, which no vanilla
client can do. Place a temporary block behind the water fan's diagonal steps.

## Layout

| Path | What |
|---|---|
| `builds/bamboo_cascade.py` | the cascade farm, every coordinate in `layout()` |
| `builds/bamboo_terrace.py`, `bamboo_grid.py`, `bamboo_wash.py`, … | earlier designs, kept for the record |
| `builds/cascade_*.py` | control circuit and sub-assemblies |
| `mcschem.py` | litemapy helpers: `block()`, `sign()`, `save()` |
| `bamboo_sizing.py` | yield and footprint arithmetic |
| `schematics/bamboo-cascade-4x16-cobble.litematic` | the small one, 64 plants — hand-tuned past the script (see “The two shipped schematics”) |
| `schematics/bamboo-cascade-8x32-cobble.litematic` | the medium, 256 plants — straight from `bamboo_cascade.py` |

The RCON harness that measured these numbers on a local test server is not
published; a few scripts here import from an `experiments/` directory that is
missing, so their `__main__` blocks will not run. The build functions do.
