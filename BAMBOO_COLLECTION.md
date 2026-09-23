# Bamboo collection on EdenMC — limits, receptacle, and capacity

All numbers below were measured on the local headless 1.21.8 rig
(`~/mcbuild/testserver`, experiments `exp28`–`exp32`), each against a control
that had to read zero, EXCEPT Eden's bamboo growth rate, which cannot be
measured locally — see "What does not transfer".

## 1. Eden's limits

From Eden's own wiki (`edenmc.miraheze.org`, page *Chunk Limits*):

| Block | Per chunk |
|---|---|
| **Hopper** | **16** |
| Piston / sticky piston | 32 each |
| Furnace / blast furnace / smoker / brewing stand | 32 each |
| Item frame / glow item frame | 32 each |
| Armor stand / painting | 48 each |

Droppers, dispensers, comparators, observers and chests are **not on the
table** — confirm with `/chunklimits` in game before designing around them.

Two other Eden facts that matter here:

* **RealisticBiomes is active** (`/rb`) — crops grow much slower than vanilla
  and only in certain biomes.
* **Citadel will not reinforce bamboo or pistons.** The crop and the breaker
  are inherently exposed; obsidian, hoppers and barrels do reinforce, so the
  collection end is the part worth diamond.

## 2. Measured mechanics

| Quantity | Measured | Control |
|---|---|---|
| Hopper → container | 150 items in 58.1 s = **2.5/s** (8 ticks/item) | powered hopper: **0** |
| One hopper, burst absorbed in 75 s | **504, 504, 503** (predicted 507) | — |
| One hopper, burst absorbed over the **full 300 s despawn window** | **1063** (predicted 1070, ratio **0.993**) | — |
| Model `5×64 + 2.5·t` predicts at 75 s | 507 | — |
| Vanilla bamboo growth `p` per random tick | **0.323 / 0.350** at tick speed 25 / 50 (≈ 1/3) | tick speed 0: **0 growths / 200 plants** |

The growth rate was measured at two tick speeds precisely so the *linearity*
could be checked, not just the constant: it held, so the model is right.


**TPS caveat.** A hopper moves one item per 8 *game* ticks. That is 2.5/s only
while the server holds 20 TPS. Repeats of the same single-hopper trial gave
504, 504, 503, 499 and 440 — the low one on a server that was visibly lagging
("Can't keep up" in the log). On a busy civ server at peak, treat 2.5/s as an
optimistic ceiling and leave headroom.

## 3. The finding that changes the design

**A row of hoppers used as the floor of a flowing stream does not share a
burst.** Identical 2048-item bursts, hoppers at the downstream end:

| Hoppers | Banked | Split |
|---|---|---|
| 1 | 504 | `[504]` |
| 4 | 697 | `[64, 64, 64, 505]` |
| 8 | 506 | `[512, 0, 0, 0, 0, 0, 0, 0]` |

Each upstream hopper catches a single stack as the wave passes; the current
pins everything else against the far wall. **Eight hoppers bank what one
hopper banks.** A hopper only counts toward capacity if it has its own drop
point.

*(Caveat: the global loose-item count is unreliable — it disagreed between
identical reps. The `banked` figures come from per-container reads and are
sound, and the split is unambiguous.)*



**Nor does removing the current help.** Dropping the crop down a shaft into a
still chamber with a 3x3 hopper floor banked 504 — all of it on the ONE hopper
under the drop, `[0,0,0,0,504,0,0,0,0]`. Reproduced dry (504, 413) and with the
chamber flooded (504): water does not help either. Item entities pile on the tile they
land on; they do not spread onto neighbouring hoppers. So a collection point is
one hopper no matter how it is shaped, and the only way to add capacity is to
add collection points.

## 4. Capacity — how many plants

Eden bamboo caps at height 10 deterministically and is broken one above the
dirt, so **9 bamboo per plant per cycle**, and one growth step = one harvested
item. Two different limits apply:

**Burst limit (harvest fires all at once).** Items despawn 5 minutes after they
drop, so one collection point can absorb

    5 slots × 64 buffered + 2.5/s × 300 s ≈ 1070 bamboo ≈ 118 plants

measured directly at the full window: **1063 banked of a 2560 burst in 310 s**,
0.7% off the model. This is not an extrapolation.

This ceiling is set by the despawn clock, so **it does not move when
RealisticBiomes slows growth.** Slower growth buys throughput, never burst
headroom.

**Throughput limit (harvest staggered).** 9000 bamboo/hour per hopper ÷ the
Eden growth rate. At the vanilla rate (17.58/plant/hour) that is exactly
**512 plants per hopper**; Eden is slower, so the real figure is higher — get
it from `/rb`.

Sizing helper: `~/mcbuild/venv/bin/python ~/mcbuild/bamboo_sizing.py <plants>
--growth-pct <from /rb> --groups <stagger groups>`

**Per chunk (16 hoppers): ~1,900 plants harvested all at once, or 8,000+ if
staggered.**

## 4b. Raising capacity at a single collection point

Two candidate escapes from the 1070 ceiling, both measured (exp33/34):

**Redstone lock pulsing — does not work.** 151 items/60 s free-running vs 137
pulsed at 5 Hz. Unlocking does not reset the 8-tick cooldown; the lock is pure
cost.

**Hopper minecarts — each adds exactly 320 of buffer.** Park N carts on a rail
on top of the intake hopper:

    burst capacity = 320*N + 2.5*t   ->   320*N + 750 at the despawn window

| carts | barrel | hopper | in carts | total | 320*N check |
|---|---|---|---|---|---|
| 0 | 195 | 320 | — | 515 | — |
| 1 | 195 | 1 | 133 | 329 | 133+187 = 320 |
| 2 | 195 | 1 | 453 | 649 | 453+187 = 640 |
| 4 | 195 | 1 | 1093 | 1289 | 1093+187 = 1280 |
| 8 | 194 | 1 | 2366 | 2561 | 2366+194 = 2560 |

Note the hopper holds **1** item once carts are present, not 320 — the carts
intercept the crop first, so you FORFEIT the hopper's own buffer. One cart is
therefore a downgrade (329 vs 515 bare); two is break-even.

Eden counts hopper minecarts in the same 16/chunk bucket as hoppers, so per unit
spent: a new drop point buys ~1070, a cart buys 320. **Split the stream when you
can — 3.3x better.** Carts are for when you cannot. Fifteen carts plus one
hopper at a single point gives ~5550 bamboo, about 616 plants in one burst.

## 5. The receptacle

`~/mcbuild/builds/bamboo_receptacle.py` → `bamboo_receptacle.litematic`
(9 × 4 × 3, 106 blocks: 104 obsidian, 1 hopper, 1 barrel, plus water).

```
  y3 lid     | . # # # # # # # # |
  y2 channel | . ~ ~ ~ ~ ~ ~ ~ # |
  y1 floor   | # # # # # # # H # |
  y0 storage | # # # # # # # B # |
              | 0 1 2 3 4 5 6 7 8 |   west -> east
```

x0 is the open inlet where the existing stream is joined; x1 is a water source
(one source spreads 7 tiles, so it covers the whole run); **x7's floor tile is
the hopper**, with the end wall right behind it and a barrel underneath.

No drop shaft: the current pins the crop against the end wall and holds it on
that hopper, which exp30 measured banking 505 of a 2048 burst — the full
single-hopper capacity. A shaft performs the same (exp31: 503) but the
channel's water pours down it, which is extra structure for no extra crop.

Swap the barrel for a double chest (3456 vs 1728) if the farm outruns it.

## 6. In terms of the grid farm

`bamboo_grid.py` is 8 plant columns per module, and its collection plan is one
trench per *column* of modules. A 5×5 grid is 200 plants over 5 trenches — **40
plants per collection point**, comfortably inside the ~118 ceiling. One hopper
per trench is plenty.

The hopper limit does not bind until roughly **1,900 plants (~236 modules, a
15×15 grid)**, and only then if every trench empties into the same chunk.
Spread the trenches across chunks and it never binds at all.

Note the grid's trench pushes water in from *both* ends so the flows meet and
stall — that removes the pinning current, which is the thing that defeated the
hopper bank in exp30.

## 7. What does not transfer from the rig

**Bamboo needs open sky on Eden.** RealisticBiomes replaces the vanilla light
rule, under which a sealed box lit by glowstone grows fine (`exp8`: 9 vs 12.25
open-sky, sealed-dark 0). On Eden that is not an option: no roofs, no vertical
stacking, single layer only. At the grid's 5.9 ground blocks per column that
makes a chunk hold ~43 plants, so one hopper's 118 plants needs ~2.7 chunks of
open ground and a full 16-hopper chunk serves a farm of ~44 chunks. The farm is
land-bound; collection never is.

The local server is vanilla creative. Eden differs in bamboo max height
(10 fixed vs 12–16 random — the rig measured `[12,13,14,16,…]`) and in growth
rate (RealisticBiomes). The hopper rate, the burst-absorption model and the
water/item behaviour are vanilla mechanics and do transfer, unless Eden has
tuned `ticks-per.hopper-transfer` — worth a one-minute check in game: fill a
hopper over a chest and time 150 items into it (should be 60 s).
