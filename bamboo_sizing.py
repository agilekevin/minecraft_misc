#!/usr/bin/env python3
"""Size a bamboo collection system for Eden. Run with ~/mcbuild/venv/bin/python.

Every constant here was measured on the local 1.21.8 rig except Eden's growth
rate, which cannot be: Eden runs RealisticBiomes, so its bamboo grows slower
than vanilla and only in some biomes. Check it in game with /rb and pass it in.

    MEASURED (exp28/29/30, each against a control that read zero)
      hopper -> container       150 items in 58.1 s  = 2.5/s = 8 ticks/item
      hopper burst absorption   320 buffered + 2.5/s   (504 of 2048 in 75 s,
                                                        twice, vs 507 predicted)
      vanilla bamboo growth     p = 1/3 per random tick on the top stalk
                                -> 17.58 stalks/plant/hour at randomTickSpeed 3

    EDEN RULES (from the user / the Eden wiki)
      bamboo caps at height 10, deterministically -- no 12..16 vanilla spread
      harvest breaks 1 above the dirt, so 9 bamboo per plant per cycle
      16 hoppers per chunk

    THE HOPPERS MUST BE AT SEPARATE COLLECTION POINTS (exp30). Lining them up
    as the floor of one flowing stream does NOT share the burst: four hoppers
    under a current split it [64, 64, 64, 505] -- each upstream hopper caught a
    single stack as the wave passed and the current pinned the rest against the
    far wall on the last one. Four hoppers banked 697 of 2048 where one banked
    504. Count a hopper toward capacity only if it has its own drop point.
"""
import argparse

HOPPER_PER_SEC = 2.5
HOPPER_SLOTS = 5
STACK = 64
DESPAWN_SEC = 300
YIELD_PER_PLANT = 9          # Eden: capped at 10, broken 1 above dirt
VANILLA_PER_PLANT_PER_HOUR = 17.58
HOPPERS_PER_CHUNK = 16       # Eden chunk limit


def burst_capacity(seconds=DESPAWN_SEC):
    """Items one hopper can swallow from a single instantaneous dump."""
    return HOPPER_SLOTS * STACK + HOPPER_PER_SEC * seconds


def report(plants, growth_pct, groups):
    g = VANILLA_PER_PLANT_PER_HOUR * growth_pct / 100.0
    burst_items = plants * YIELD_PER_PLANT / groups
    cap = burst_capacity()

    hop_burst = burst_items / cap
    hop_steady = plants * g / (HOPPER_PER_SEC * 3600)
    need = max(hop_burst, hop_steady)

    print(f"  plants                {plants}")
    print(f"  growth rate           {growth_pct}% of vanilla "
          f"= {g:.2f} bamboo/plant/hour")
    print(f"  harvest groups        {groups} "
          f"({'all at once' if groups == 1 else 'staggered'})")
    print(f"  output                {plants * g:,.0f} bamboo/hour "
          f"= {plants * g / 64:,.1f} stacks/hour")
    print(f"  cycle time            {YIELD_PER_PLANT / g:.1f} h per plant"
          if g else "  cycle time            n/a")
    print()
    print(f"  burst per harvest     {burst_items:,.0f} bamboo")
    print(f"  hoppers for burst     {hop_burst:.2f}  (cap {cap:.0f} each)")
    print(f"  hoppers for average   {hop_steady:.2f}")
    print(f"  --> HOPPERS NEEDED    {-(-need // 1):.0f}   "
          f"({'burst' if hop_burst >= hop_steady else 'throughput'}-limited)")
    print(f"      chunks at 16/ea   {-(-need / HOPPERS_PER_CHUNK // 1):.0f}")
    print(f"  storage fill time     a double chest (3456) every "
          f"{3456 / (plants * g):.1f} h" if plants * g else "")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("plants", type=int)
    ap.add_argument("--growth-pct", type=float, default=100.0,
                    help="Eden bamboo growth as %% of vanilla (check /rb)")
    ap.add_argument("--groups", type=int, default=1,
                    help="harvest split into N staggered groups")
    a = ap.parse_args()
    print()
    report(a.plants, a.growth_pct, a.groups)
    print()
    print(f"  one hopper holds {burst_capacity():.0f} bamboo from one dump "
          f"= {burst_capacity() / YIELD_PER_PLANT:.0f} plants,")
    print("  regardless of growth rate -- the despawn clock sets that, not /rb.")
