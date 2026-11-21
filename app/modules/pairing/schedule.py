from collections import defaultdict

from app.modules.pairing.matching import optimal_matching
from app.timebase import seconds, utc


def schedule(spec, rows, index):
    start, end = seconds(spec.start), seconds(spec.end)
    per_cabinet = defaultdict(lambda: {"upper": [], "lower": []})
    for row in rows:
        if row["disposition"] == "accepted":
            position = row["deployment"]
            per_cabinet[position["cabinet"]][position["level"]].append(row)
    slots = []
    unused = []
    for cabinet in spec.cabinet_hours:
        levels = per_cabinet[cabinet.id]
        upper_slots = defaultdict(list)
        for row in levels["upper"]:
            slot = start + (row["measured"] - start) // 3600 * 3600
            upper_slots[slot].append(row)
        anchor_slots = sorted(upper_slots)
        ranked = [sorted(upper_slots[slot], key=lambda row: (abs(row["measured"] - slot - 1800), row["measured"], row["line"]))
                  for slot in anchor_slots]
        lowers = sorted(levels["lower"], key=lambda row: (row["measured"], row["line"]))
        matches, candidates = optimal_matching(ranked, lowers, spec.tolerance_seconds, index)
        used = {lower for _, lower in matches.values()}
        unused.extend({"id": row["id"], "code": "UNUSED_LOWER", "cabinet": cabinet.id}
                      for j, row in enumerate(lowers) if j not in used)
        position = {slot: i for i, slot in enumerate(anchor_slots)}
        for hour in range(start, end, 3600):
            i = position.get(hour)
            rank, j = matches.get(i, (0, None))
            upper = ranked[i][rank] if i is not None else None
            lower = lowers[j] if j is not None else None
            if i is not None:
                unused.extend({"id": row["id"], "code": "EXTRA_UPPER", "cabinet": cabinet.id}
                              for n, row in enumerate(ranked[i]) if n != rank)
            code = None if lower else "MISSING_UPPER" if upper is None else "LOWER_CONTENTION" if i in candidates else "NO_COMPATIBLE_LOWER"
            slots.append({"cabinet": cabinet.id, "hour": hour, "start": utc(hour), "end": utc(hour+3600),
                          "upper": upper["id"] if upper else None, "lower": lower["id"] if lower else None,
                          "drift": abs(lower["measured"]-upper["measured"]) if lower else None, "code": code})
    return slots, unused
