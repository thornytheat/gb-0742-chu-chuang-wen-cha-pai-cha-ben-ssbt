from app.modules.audit.reconcile import reconcile_tickets, ticket_times
from app.modules.archive.pipeline import evaluate
from app.modules.intake.catalog import load_sample
from app.modules.intake.contract import Shift, Ticket
from app.timebase import utc


def handover():
    return evaluate(load_sample("handover"))


def claims_by_id(snapshot):
    return {claim["episode"]: claim for claim in snapshot["audit"]["claims"]}


def synthetic(tickets, kind="SUSTAINED", hours=("2026-11-20T01:00:00Z", "2026-11-20T02:00:00Z")):
    spec = Shift.model_validate({
        "sample": "synthetic", "label": "合成", "shift": "S1", "start": "2026-11-20T08:00:00+08:00",
        "end": "2026-11-20T12:00:00+08:00",
        "cabinet_hours": [{"id": "CV-17", "label": "柜", "upper_mm": 1500, "lower_mm": 500,
                           "temp_limit": "2.0", "rh_limit": "8.0"}],
        "tolerance_seconds": 240, "late_seconds": 900, "sustained_hours": 2,
        "deployments": [{"probe": "0001", "cabinet": "CV-17", "level": "upper",
                         "start": "2026-11-20T08:00:00+08:00", "end": "2026-11-20T12:00:00+08:00"}],
        "tickets": tickets, "csv": "synthetic.csv", "records": 1})
    grades = [{"cabinet": "CV-17", "hour": 1795136400 + 3600 * n, "start": hour, "state": "ABNORMAL",
               "upper": None, "lower": None} for n, hour in enumerate(hours)]
    end = utc(1795136400 + 3600 * len(hours))
    episodes = [{"id": "CV-17-A01", "cabinet": "CV-17", "kind": kind, "start": hours[0],
                 "end": end, "hours": len(hours),
                 "evidence": [{"start": hour, "upper": None, "lower": None} for hour in hours]}]
    return reconcile_tickets(spec, grades, episodes)


def test_cancelled_ticket_stays_in_handover_but_never_closes_the_episode():
    claims = claims_by_id(handover())
    closed = claims["CV-17-A01"]
    assert closed["status"] == "CLOSED" and closed["responsible"] == "AL-0801"
    assert "AL-0805" in closed["tickets"] and closed["cancelled_tickets"] == ["AL-0805"]
    verdict = {row["id"]: row["code"] for row in handover()["audit"]["tickets"]}
    assert verdict["AL-0805"] == "CANCELLED"


def test_cancelled_ticket_with_same_coverage_cannot_be_the_responsible_one():
    snapshot = handover()
    claim = claims_by_id(snapshot)["CV-17-A01"]
    assert claim["cancelled_tickets"] == ["AL-0805"]
    assert claim["responsible"] != "AL-0805"
    assert claim["covered_hours"] == ["2026-11-20T01:00:00Z", "2026-11-20T02:00:00Z"]


def test_late_ticket_only_proves_hours_from_arrival_onward():
    snapshot = handover()
    claim = claims_by_id(snapshot)["CV-17-A03"]
    assert claim["status"] == "PARTIAL" and claim["reason"] == "LATE_ARRIVAL"
    assert claim["responsible"] == "AL-0802"
    assert claim["covered_hours"] == ["2026-11-20T08:00:00Z"]
    assert claim["uncovered_hours"] == ["2026-11-20T07:00:00Z"]
    assert [(row["hour"][11:16], row["tickets"]) for row in claim["hour_claims"]] == [
        ("07:00", []), ("08:00", ["AL-0802"])]


def test_arrival_inside_an_hour_does_not_cover_that_whole_hour():
    _, claims = synthetic([
        {"id": "T1", "cabinet": "CV-17", "at": "2026-11-20T09:05:00+08:00", "arrived": "2026-11-20T10:20:00+08:00"},
    ], hours=("2026-11-20T01:00:00Z", "2026-11-20T02:00:00Z", "2026-11-20T03:00:00Z"))
    claim = claims[0]
    assert claim["covered_hours"] == ["2026-11-20T03:00:00Z"]
    assert claim["uncovered_hours"] == ["2026-11-20T01:00:00Z", "2026-11-20T02:00:00Z"]


def test_episode_without_any_ticket_stays_open_with_reason():
    claim = claims_by_id(evaluate(load_sample("shift")))["CV-17-A03"]
    assert claim["status"] == "OPEN" and claim["reason"] == "NO_TICKET"
    assert claim["uncovered_hours"] == ["2026-11-20T07:00:00Z", "2026-11-20T08:00:00Z"]


def test_handover_summary_lists_unclosed_episodes_and_their_missing_hours():
    summary = handover()["audit"]["claim_summary"]
    assert (summary["episodes"], summary["closed"], summary["partial"], summary["open"]) == (3, 1, 1, 0)
    assert summary["unclosed"] == [{
        "episode": "CV-17-A03", "status": "PARTIAL", "reason": "LATE_ARRIVAL",
        "note": "到场晚于段首，前段柜时仍缺处置", "responsible": "AL-0802",
        "cancelled_tickets": ["AL-0803"], "uncovered_hours": ["2026-11-20T07:00:00Z"]}]
    assert summary["uncovered_hours"] == ["2026-11-20T07:00:00Z"]


def test_later_ticket_arriving_after_the_responsible_one_only_repeats_hours():
    reviews, claims = synthetic([
        {"id": "T1", "cabinet": "CV-17", "at": "2026-11-20T09:05:00+08:00", "arrived": "2026-11-20T10:00:00+08:00"},
        {"id": "T2", "cabinet": "CV-17", "at": "2026-11-20T09:20:00+08:00", "arrived": "2026-11-20T11:00:00+08:00"},
    ], hours=("2026-11-20T01:00:00Z", "2026-11-20T02:00:00Z", "2026-11-20T03:00:00Z"))
    claim = claims[0]
    assert (claim["status"], claim["responsible"]) == ("PARTIAL", "T1")
    assert claim["covered_hours"] == ["2026-11-20T02:00:00Z", "2026-11-20T03:00:00Z"]
    assert claim["uncovered_hours"] == ["2026-11-20T01:00:00Z"]
    assert {row["id"]: row["code"] for row in reviews} == {"T1": "MATCHED", "T2": "DUPLICATE_ALARM"}
    assert claim["hour_claims"][2]["tickets"] == ["T1", "T2"]


def test_ticket_arriving_after_the_episode_ends_proves_nothing():
    reviews, claims = synthetic([
        {"id": "T1", "cabinet": "CV-17", "at": "2026-11-20T09:05:00+08:00", "arrived": "2026-11-20T13:00:00+08:00"},
    ])
    claim = claims[0]
    assert (claim["status"], claim["reason"], claim["responsible"]) == ("OPEN", "ARRIVED_AFTER_EPISODE", None)
    assert claim["uncovered_hours"] == ["2026-11-20T01:00:00Z", "2026-11-20T02:00:00Z"]
    assert [row["code"] for row in reviews] == ["ARRIVED_AFTER_EPISODE"]


def test_episode_with_only_cancelled_tickets_cannot_be_reported_as_handled():
    reviews, claims = synthetic([
        {"id": "T1", "cabinet": "CV-17", "at": "2026-11-20T09:05:00+08:00", "status": "CANCELLED"},
        {"id": "T2", "cabinet": "CV-17", "at": "2026-11-20T09:10:00+08:00", "status": "CANCELLED",
         "arrived": "2026-11-20T09:30:00+08:00"},
    ])
    claim = claims[0]
    assert (claim["status"], claim["reason"]) == ("OPEN", "ALL_TICKETS_CANCELLED")
    assert claim["cancelled_tickets"] == ["T1", "T2"] and claim["tickets"] == ["T1", "T2"]
    assert claim["responsible"] is None and claim["covered_hours"] == []
    assert [row["code"] for row in reviews] == ["CANCELLED", "CANCELLED"]


def test_cancelled_ticket_never_becomes_responsible_even_with_a_later_active_one():
    reviews, claims = synthetic([
        {"id": "T1", "cabinet": "CV-17", "at": "2026-11-20T09:05:00+08:00", "status": "CANCELLED"},
        {"id": "T2", "cabinet": "CV-17", "at": "2026-11-20T09:20:00+08:00", "arrived": "2026-11-20T10:00:00+08:00"},
    ])
    claim = claims[0]
    assert (claim["status"], claim["responsible"]) == ("PARTIAL", "T2")
    assert claim["cancelled_tickets"] == ["T1"]
    assert claim["uncovered_hours"] == ["2026-11-20T01:00:00Z"]
    assert {row["id"]: row["code"] for row in reviews} == {"T1": "CANCELLED", "T2": "MATCHED"}


def test_transient_blip_is_not_a_handover_segment_even_when_a_ticket_matches():
    _, claims = synthetic([
        {"id": "T1", "cabinet": "CV-17", "at": "2026-11-20T09:05:00+08:00"},
    ], kind="TRANSIENT", hours=("2026-11-20T01:00:00Z",))
    claim = claims[0]
    assert (claim["status"], claim["reason"], claim["responsible"]) == ("TRANSIENT", "TRANSIENT_ONLY", "T1")


def test_ticket_aliases_normalize_without_losing_cancel_semantics():
    cancelled = Ticket.model_validate({"id": "T1", "cabinet": "CV-17", "at": "2026-11-20T09:00:00+08:00",
                                      "state": "撤销", "arrived_at": "2026-11-20T10:00:00+08:00"})
    assert (cancelled.status, cancelled.arrived) == ("CANCELLED", "2026-11-20T10:00:00+08:00")
    assert ticket_times(cancelled) == (1795136400, 1795140000, 1795140000)
    flag = Ticket.model_validate({"id": "T2", "cabinet": "CV-17", "at": "2026-11-20T09:00:00+08:00",
                                  "cancelled": "true"})
    assert flag.status == "CANCELLED"


def test_unknown_ticket_status_is_rejected_rather_than_guessed():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Ticket.model_validate({"id": "T3", "cabinet": "CV-17", "at": "2026-11-20T09:00:00+08:00",
                               "status": "CLOSED"})


def test_arrival_before_alarm_is_rejected():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Ticket.model_validate({"id": "T2", "cabinet": "CV-17", "at": "2026-11-20T09:00:00+08:00",
                               "arrived": "2026-11-20T08:00:00+08:00"})


def test_api_claims_match_archived_result(client):
    created = client.post("/api/runs", json={"sample": "handover"}).json()["manifest"]
    result = client.get(f'/api/runs/{created["id"]}/claims').json()
    assert result["summary"] == created["claim_summary"]
    assert [claim["status"] for claim in result["claims"]] == ["CLOSED", "TRANSIENT", "PARTIAL"]
    assert result["summary"]["unclosed"][0]["episode"] == "CV-17-A03"


def test_replaying_handover_reuses_the_claim_ledger(client):
    first = client.post("/api/runs", json={"sample": "handover"}).json()
    second = client.post("/api/runs", json={"sample": "handover"}).json()
    assert first["manifest"] == second["manifest"] and second["reused"]
    assert len(client.get("/api/runs").json()) == 1


def test_exported_evidence_carries_the_claim_ledger_and_unclosed_reason(client):
    created = client.post("/api/runs", json={"sample": "handover"}).json()["manifest"]
    evidence = client.get(f'/api/runs/{created["id"]}/export').json()["evidence"]
    claim = {item["episode"]: item for item in evidence["audit"]["claims"]}["CV-17-A03"]
    assert (claim["status"], claim["reason"], claim["responsible"]) == ("PARTIAL", "LATE_ARRIVAL", "AL-0802")
    assert claim["cancelled_tickets"] == ["AL-0803"]
    assert claim["uncovered_hours"] == ["2026-11-20T07:00:00Z"]
    assert evidence["audit"]["claim_summary"] == created["claim_summary"]
