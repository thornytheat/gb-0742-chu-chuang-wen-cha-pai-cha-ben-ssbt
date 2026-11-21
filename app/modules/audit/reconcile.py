from collections import Counter

from app.timebase import seconds, utc

STATES = ("STABLE", "ABNORMAL", "MISSING")
DISPOSITIONS = ("accepted", "duplicate", "isolated", "blank", "header")


def reconcile_tickets(spec, grades, episodes):
    slots = {(slot["cabinet"], slot["hour"]): slot for slot in grades}
    spans = {(item["cabinet"], seconds(proof["start"])): item for item in episodes for proof in item["evidence"]}
    cabins = {item.id for item in spec.cabinet_hours}
    used = set()
    reviews = []
    order = sorted(spec.tickets, key=lambda ticket: (seconds(ticket.at), ticket.id))
    for ticket in order:
        epoch = seconds(ticket.at)
        hour = epoch // 3600 * 3600
        key = (ticket.cabinet, hour)
        slot = slots.get(key)
        episode = spans.get(key)
        if ticket.cabinet not in cabins:
            code = "UNKNOWN_CABINET"
        elif slot is None:
            code = "OUTSIDE_SHIFT"
        elif slot["state"] == "MISSING":
            code = "MISSING_EVIDENCE"
        elif slot["state"] == "STABLE":
            code = "STABLE_AT_ALARM"
        elif episode is None or episode["kind"] == "TRANSIENT":
            code = "TRANSIENT_ONLY"
        elif episode["id"] in used:
            code = "DUPLICATE_ALARM"
        else:
            code = "MATCHED"
            used.add(episode["id"])
        reviews.append({**ticket.model_dump(), "at_utc": utc(epoch), "code": code,
                        "slot": slot["start"] if slot else None, "episode": episode["id"] if episode else None,
                        "evidence": [slot[level] for level in ("upper", "lower") if slot and slot[level]]})
    return reviews, [item["id"] for item in episodes if item["kind"] == "SUSTAINED" and item["id"] not in used]


def reconcile(spec, rows, intake, grades, episodes):
    begin, end = seconds(spec.start), seconds(spec.end)
    expected = {(cabinet.id, hour) for cabinet in spec.cabinet_hours for hour in range(begin, end, 3600)}
    seen = Counter((slot["cabinet"], slot["hour"]) for slot in grades)
    tally = Counter(slot["state"] for slot in grades)
    hours = {"expected": len(expected), **{state.lower(): tally[state] for state in STATES},
             "missing_keys": [[cabinet, utc(hour)] for cabinet, hour in sorted(expected - seen.keys())],
             "extra_keys": [[cabinet, utc(hour)] for cabinet, hour in sorted(seen.keys() - expected)],
             "duplicate_keys": [[cabinet, utc(hour)] for (cabinet, hour), count in sorted(seen.items()) if count > 1]}
    hours["balanced"] = (not (hours["missing_keys"] or hours["extra_keys"] or hours["duplicate_keys"])
                         and len(expected) == sum(tally[state] for state in STATES))
    counted = Counter(row["disposition"] for row in rows)
    row_audit = {"total": len(rows), "declared": intake["declared"], **{key: counted[key] for key in DISPOSITIONS}}
    row_audit["balanced"] = len(rows) == sum(row_audit[key] for key in DISPOSITIONS) and (
        intake["declared"] == counted["accepted"] + counted["duplicate"] + counted["isolated"])
    tickets, unreported = reconcile_tickets(spec, grades, episodes)
    return {"hours": hours, "row_audit": row_audit, "tickets": tickets, "unreported": unreported,
            "ticket_counts": dict(Counter(ticket["code"] for ticket in tickets))}
