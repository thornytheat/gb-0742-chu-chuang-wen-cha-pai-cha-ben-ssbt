from collections import Counter

from app.reasons import REASONS
from app.timebase import seconds, utc

STATES = ("STABLE", "ABNORMAL", "MISSING")
DISPOSITIONS = ("accepted", "duplicate", "isolated", "blank", "header")
HOUR = 3600

# Claim status per abnormal episode, in handover order:
# CLOSED    every abnormal cabinet hour is proven handled by an active ticket
# PARTIAL   some hours are proven, the rest still lack handling
# OPEN      no hour is proven handled
# TRANSIENT a single-hour blip, not a sustained segment the handover must close
CLAIM_STATUSES = ("CLOSED", "PARTIAL", "OPEN", "TRANSIENT")


def hour_start(epoch):
    return epoch // HOUR * HOUR


def ticket_times(ticket):
    """Alarm, arrival and the first cabinet hour the ticket can prove.

    Cabinet hours are half-open ``[hour, hour + 1h)``.  A late ticket only
    proves the cabinet hours that begin at or after its arrival: a handler who
    arrives at 16:20 was not present for the start of the 16:00 hour, so that
    hour stays unproven.  The hours between the alarm and the arrival are never
    proven either.  Without an arrival stamp the alarm hour itself is the first
    proven hour, which keeps handovers that predate arrival stamps readable.
    """
    alarm = seconds(ticket.at)
    if ticket.arrived is None:
        return alarm, alarm, hour_start(alarm)
    arrival = seconds(ticket.arrived)
    return alarm, arrival, -(-arrival // HOUR) * HOUR


def _episode_index(episodes):
    """Map each abnormal cabinet hour to its episode, and list episode hours."""
    by_hour, hours = {}, {}
    for episode in episodes:
        starts = sorted(seconds(proof["start"]) for proof in episode["evidence"])
        hours[episode["id"]] = starts
        for proof in episode["evidence"]:
            by_hour[(episode["cabinet"], seconds(proof["start"]))] = episode
    return by_hour, hours


def _ordered(items):
    return sorted(items, key=lambda item: (item["alarm"], item["ticket"].id))


def _claim(episode, referenced, episode_hours):
    """One line of the handover ledger for one episode.

    An active ticket proves the cabinet hours from its arrival hour through the
    end of the episode; a late record therefore leaves the hours between the
    alarm and the arrival unproven.  Cancelled tickets stay in the ledger by
    number so the original alarm never disappears from the handover, but they
    never prove an hour: withdrawal means the handling did not happen, so the
    episode cannot count as reported.  The active ticket with the earliest
    arrival is the responsible one; the rest repeat hours already proven.
    """
    end = seconds(episode["end"])
    ordered = _ordered(referenced)
    transient = episode["kind"] == "TRANSIENT"
    covering = []
    for item in ordered:
        if item["ticket"].status != "ACTIVE":
            item["coverage"], item["role"] = [], "CANCELLED"
            continue
        item["coverage"] = [hour for hour in episode_hours if item["effective"] <= hour < end]
        if not item["coverage"]:
            item["role"] = "OUT_OF_COVERAGE"
        else:
            covering.append(item)
    covering.sort(key=lambda item: (item["coverage"][0], item["alarm"], item["ticket"].id))
    covered = set()
    responsible = covering[0]["ticket"].id if covering else None
    hour_claims = {}
    for item in covering:
        covered.update(item["coverage"])
        for hour in item["coverage"]:
            hour_claims.setdefault(hour, []).append(item["ticket"].id)
        if transient:
            item["role"] = "TRANSIENT"
        elif item["ticket"].id == responsible:
            item["role"] = "RESPONSIBLE"
        else:
            # Coverage runs from the arrival hour to the episode end, so the
            # earliest arrival proves a superset of every later one.
            item["role"] = "DUPLICATE"
    uncovered = sorted(set(episode_hours) - covered)
    cancelled = [item["ticket"].id for item in ordered if item["ticket"].status == "CANCELLED"]
    if transient:
        status, reason = "TRANSIENT", "TRANSIENT_ONLY"
    elif not ordered:
        status, reason = "OPEN", "NO_TICKET"
    elif not any(item["ticket"].status == "ACTIVE" for item in ordered):
        status, reason = "OPEN", "ALL_TICKETS_CANCELLED"
    elif not uncovered:
        status, reason = "CLOSED", None
    elif covered:
        status, reason = "PARTIAL", "LATE_ARRIVAL"
    else:
        status, reason = "OPEN", "ARRIVED_AFTER_EPISODE"
    return {"episode": episode["id"], "cabinet": episode["cabinet"], "kind": episode["kind"],
            "start": episode["start"], "end": episode["end"], "hours": episode["hours"],
            "status": status, "responsible": responsible, "reason": reason,
            "note": REASONS[reason] if reason else None,
            "tickets": [item["ticket"].id for item in ordered],
            "cancelled_tickets": cancelled,
            "covered_hours": [utc(hour) for hour in sorted(covered)],
            "uncovered_hours": [utc(hour) for hour in uncovered],
            "hour_claims": [{"hour": utc(hour), "tickets": hour_claims.get(hour, [])} for hour in episode_hours],
            "arrived_late": any(item["late"] for item in ordered if item["ticket"].status == "ACTIVE")}


def reconcile_tickets(spec, grades, episodes):
    """Pair tickets with abnormal episodes and build the handover claim ledger."""
    slots = {(slot["cabinet"], slot["hour"]): slot for slot in grades}
    by_hour, episode_hours = _episode_index(episodes)
    cabins = {item.id for item in spec.cabinet_hours}
    order = sorted(spec.tickets, key=lambda ticket: (seconds(ticket.at), ticket.id))
    referenced = {episode["id"]: [] for episode in episodes}
    prepared = []
    for ticket in order:
        alarm, arrival, effective = ticket_times(ticket)
        episode = by_hour.get((ticket.cabinet, hour_start(alarm)))
        item = {"ticket": ticket, "alarm": alarm, "arrival": arrival, "effective": effective,
                "late": arrival > alarm, "episode": episode, "coverage": [], "role": None}
        prepared.append(item)
        if episode is not None:
            referenced[episode["id"]].append(item)

    claims = [_claim(episode, referenced[episode["id"]], episode_hours[episode["id"]]) for episode in episodes]
    by_episode = {claim["episode"]: claim for claim in claims}

    reviews = []
    for item in prepared:
        ticket, alarm, arrival, episode = item["ticket"], item["alarm"], item["arrival"], item["episode"]
        slot = slots.get((ticket.cabinet, hour_start(alarm)))
        if ticket.cabinet not in cabins:
            code = "UNKNOWN_CABINET"
        elif slot is None:
            code = "OUTSIDE_SHIFT"
        elif ticket.status == "CANCELLED":
            code = "CANCELLED"
        elif slot["state"] == "MISSING":
            code = "MISSING_EVIDENCE"
        elif slot["state"] == "STABLE":
            code = "STABLE_AT_ALARM"
        elif episode is None:
            code = "TRANSIENT_ONLY"
        else:
            code = {"RESPONSIBLE": "MATCHED", "TRANSIENT": "TRANSIENT_ONLY",
                    "DUPLICATE": "DUPLICATE_ALARM", "OUT_OF_COVERAGE": "ARRIVED_AFTER_EPISODE"}[item["role"]]
        reviews.append({**ticket.model_dump(), "at_utc": utc(alarm), "code": code,
                        "slot": slot["start"] if slot else None, "slot_state": slot["state"] if slot else None,
                        "episode": episode["id"] if episode else None,
                        "arrived_utc": utc(arrival) if ticket.arrived else None,
                        "effective_from": utc(item["effective"]), "late": item["late"],
                        "covered_hours": [utc(hour) for hour in item["coverage"]],
                        "evidence": [slot[level] for level in ("upper", "lower") if slot and slot[level]]})
    return reviews, claims


def claim_summary(claims):
    counted = Counter(claim["status"] for claim in claims)
    unclosed = [claim for claim in claims if claim["kind"] == "SUSTAINED" and claim["status"] != "CLOSED"]
    uncovered = sorted({hour for claim in unclosed for hour in claim["uncovered_hours"]})
    return {"episodes": len(claims), **{state.lower(): counted[state] for state in CLAIM_STATUSES},
            "unclosed": [{"episode": claim["episode"], "status": claim["status"], "reason": claim["reason"],
                          "note": claim["note"], "responsible": claim["responsible"],
                          "cancelled_tickets": claim["cancelled_tickets"],
                          "uncovered_hours": claim["uncovered_hours"]} for claim in unclosed],
            "uncovered_hours": uncovered}


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
    tickets, claims = reconcile_tickets(spec, grades, episodes)
    summary = claim_summary(claims)
    return {"hours": hours, "row_audit": row_audit, "tickets": tickets, "claims": claims,
            "unreported": [item["episode"] for item in summary["unclosed"]],
            "unclosed": summary["unclosed"], "claim_summary": summary,
            "ticket_counts": dict(Counter(ticket["code"] for ticket in tickets))}
