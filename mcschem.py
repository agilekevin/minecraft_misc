"""Helpers for writing .litematic files Litematica will accept.

litemapy writes the schematic format; this wraps it so every build gets the
right Minecraft data version and lands where Litematica looks, without each
build script having to remember either.

Run any build with the venv here:

    ~/mcbuild/venv/bin/python ~/mcbuild/builds/<name>.py
"""
import os
from pathlib import Path

from litemapy import BlockState, Region, Schematic

# 1.21.8, read from the client jar's own version.json rather than remembered:
#
#     unzip -p minecraft-client.jar version.json  ->  "world_version": 4440
#
# litemapy defaults to 2975 (1.18.2). Litematica will usually still load an
# older stamp, but it tells the mod to interpret block states as that version's,
# and anything whose state changed since would be re-read or dropped. Stamping
# the truth costs nothing and removes the question.
MC_DATA_VERSION = 4440

# Where Litematica looks. The Modrinth profile, not a vanilla .minecraft.
# Where save() writes. Point MCBUILD_SCHEMATIC_DIR at your Litematica
# "schematics" folder (on WSL that is under /mnt/c/Users/<you>/AppData/Roaming/...);
# without it, builds land in ./schematics next to this file.
SCHEMATIC_DIR = Path(
    os.environ.get("MCBUILD_SCHEMATIC_DIR", Path(__file__).parent / "schematics")
)

AIR = BlockState("minecraft:air")


def block(block_id: str, **states) -> BlockState:
    """A block state, e.g. block("oak_stairs", facing="north", half="top").

    The namespace is added when it is missing, since "minecraft:" on every
    single line makes a build script much harder to read than it needs to be.
    """
    if ":" not in block_id:
        block_id = f"minecraft:{block_id}"
    return BlockState(block_id, **states) if states else BlockState(block_id)


def region(width: int, height: int, depth: int) -> Region:
    """An empty region anchored at the origin.

    Coordinates are x east, y up, z south, all non-negative — Litematica places
    the whole thing relative to wherever you put the placement, so there is no
    reason for a build to think in world coordinates.
    """
    return Region(0, 0, 0, width, height, depth)


def save(reg: Region, filename: str, name: str, description: str = "") -> Path:
    """Write the region out, then read it back before claiming success.

    Reading back matters: a corrupt or empty file saves perfectly happily, and
    the failure would otherwise surface as a schematic that silently will not
    load in game, several minutes later.
    """
    if not filename.endswith(".litematic"):
        filename += ".litematic"
    out = SCHEMATIC_DIR / filename

    schem = reg.as_schematic(
        name=name,
        author="Claude",
        description=description,
        mc_version=MC_DATA_VERSION,
    )
    schem.save(str(out))

    back = Schematic.load(str(out))
    r = next(iter(back.regions.values()))
    solid = sum(
        1
        for x in range(abs(r.width))
        for y in range(abs(r.height))
        for z in range(abs(r.length))
        if r[x, y, z].id != "minecraft:air"
    )
    print(f"wrote {out}")
    print(f"  {abs(r.width)}x{abs(r.height)}x{abs(r.length)}, {solid} non-air blocks, "
          f"data version {MC_DATA_VERSION}")
    return out


# ── Version signs ────────────────────────────────────────────────────────────
#
# Every build stamps its own version into a sign, so the thing standing in the
# world can be identified without guessing. We have already had one round of
# confusion over which iteration was pasted; a sign costs one block.

def sign(reg, x, y, z, lines, rotation=0, wood="oak", back=None):
    """Place a standing sign carrying up to four lines of text.

    `rotation` is the FRONT face's direction: 0 south, 4 west, 8 north,
    12 east. Getting it wrong is silent -- a sign whose front is pressed
    against the block it stands beside places perfectly happily and is
    simply unreadable. Pass `back` to repeat the text on the far face.

    Signs use front_text/back_text with four messages each, not the old
    Text1..Text4. The messages are PLAIN STRINGS, not JSON: up to 1.21.4 they
    were JSON text components and from 1.21.5 they are NBT text components, for
    which a bare string is the literal form. Writing the JSON wrapper on 1.21.5+
    does not error — the sign just displays {"text":"..."} exactly as typed,
    which is how this was found.
    """
    from litemapy import TileEntity
    from nbtlib.tag import Byte, Compound, Int, List, String

    reg[x, y, z] = block(f"{wood}_sign", rotation=str(rotation), waterlogged="false")

    def side(msgs):
        padded = (list(msgs) + ["", "", "", ""])[:4]
        return Compound({
            "messages": List[String]([String(m) for m in padded]),
            "color": String("black"),
            "has_glowing_text": Byte(0),
        })

    reg.tile_entities.append(TileEntity(Compound({
        "x": Int(x), "y": Int(y), "z": Int(z),
        "front_text": side(lines),
        "back_text": side(back or []),
        "is_waxed": Byte(0),
    })))


def container(reg, x, y, z, state, items):
    """Place a container block carrying an inventory.

    items: [(slot, item_id, count), ...]

    Note that whether this SURVIVES a paste is up to Litematica, not the file.
    With `pasteNbtRestoreBehavior` set to "none" -- its default -- the block
    arrives empty, and pasting via /fill drops block entities as well. The
    inventory is written anyway so the schematic is complete and correct; see
    the build docstrings for the one-command loader to use when it does not.
    """
    from litemapy import TileEntity
    from nbtlib.tag import Byte, Compound, Int, List, String

    reg[x, y, z] = state
    slots = []
    for slot, item_id, count in items:
        if ":" not in item_id:
            item_id = f"minecraft:{item_id}"
        # 1.20.5 renamed this: `count` as an int, not `Count` as a byte. The
        # old spelling is accepted silently and leaves the container empty.
        slots.append(Compound({"Slot": Byte(slot),
                               "id": String(item_id),
                               "count": Int(count)}))
    reg.tile_entities.append(TileEntity(Compound({
        "x": Int(x), "y": Int(y), "z": Int(z),
        "Items": List[Compound](slots),
    })))
