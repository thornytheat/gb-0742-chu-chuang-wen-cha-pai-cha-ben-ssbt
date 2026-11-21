from app.modules.assignment.windows import DeploymentIndex
from app.timebase import seconds


def test_adjacent_windows_are_half_open_at_exact_move(package):
    # TRAP-23
    index = DeploymentIndex(package.spec)
    before, edge = [index.resolve("0008", seconds(moment)) for moment in ("2026-11-20T04:59:59Z","2026-11-20T05:00:00Z")]
    assert (before[0]["cabinet"], before[0]["id"]) == ("CV-21","D02")
    assert (edge[0]["cabinet"], edge[0]["id"]) == ("CV-17","D05")
    assert index.conflicts == []


def test_late_reading_keeps_old_position_after_receipt_moves(snapshot):
    # TRAP-13
    late = [row for row in snapshot["rows"] if "LATE_RECEIPT" in row.get("flags",[])]
    assert len(late) == 1
    assert (late[0]["probe"],late[0]["delay"],late[0]["deployment"]["cabinet"]) == ("0008",3600,"CV-21")
    assert late[0]["received_utc"] == "2026-11-20T05:10:00Z"


def test_second_probe_at_same_position_marks_overlap_only(package):
    # TRAP-25
    windows = package.spec.deployments
    overlap = windows[0].model_copy(update={"probe":"0077","start":"2026-11-20T02:00:00Z","end":"2026-11-20T03:00:00Z"})
    index = DeploymentIndex(package.spec.model_copy(update={"deployments":windows+[overlap]}))
    assert index.resolve("0001",seconds("2026-11-20T02:10:00Z")) == (None,"DEPLOYMENT_CONFLICT")
    assert index.resolve("0077",seconds("2026-11-20T02:59:59Z")) == (None,"DEPLOYMENT_CONFLICT")
    assert index.resolve("0001",seconds("2026-11-20T03:00:00Z"))[1] is None
    assert index.conflicts == [{"deployments":["D01","D07"],"start":"2026-11-20T02:00:00Z","end":"2026-11-20T03:00:00Z",
                                "probe_conflict":False,"position_conflict":True}]


def test_same_probe_in_two_cabinets_is_ambiguous(package):
    windows = package.spec.deployments
    overlap = windows[0].model_copy(update={"cabinet":"CV-21","level":"lower"})
    index = DeploymentIndex(package.spec.model_copy(update={"deployments":windows+[overlap]}))
    assert index.resolve("0001",seconds("2026-11-20T03:00:00Z")) == (None,"DEPLOYMENT_CONFLICT")
    assert any(entry["probe_conflict"] for entry in index.conflicts)


def test_distinguishes_unassigned_probe_and_shift_right_boundary(snapshot):
    rows = {row["code"]:row for row in snapshot["rows"] if row["code"] in {"OFF_SHIFT","NO_DEPLOYMENT"}}
    assert rows["NO_DEPLOYMENT"]["probe"] == "0099"
    assert rows["OFF_SHIFT"]["observed_utc"] == "2026-11-20T10:00:00Z"


def test_lookup_uses_offset_and_rejects_naive_time(client, base):
    url = base + "/assignment/lookup"
    result = client.get(url, params={"probe":"0001","at":"2026-11-20T13:00:00+08:00"}).json()
    assert (result["deployment"]["cabinet"],result["deployment"]["level"]) == ("CV-21","upper")
    invalid = client.get(url, params={"probe":"0001","at":"2026-11-20T13:00:00"})
    assert (invalid.status_code,invalid.json()["code"]) == (422,"BAD_TIME")


def test_continuity_disallows_crossing_short_conflicting_interval(package):
    windows = package.spec.deployments
    overlap = windows[0].model_copy(update={"probe":"0077","start":"2026-11-20T02:02:00Z","end":"2026-11-20T02:03:00Z"})
    index = DeploymentIndex(package.spec.model_copy(update={"deployments":windows+[overlap]}))
    early, late = [seconds(value) for value in ("2026-11-20T02:01:00Z","2026-11-20T02:04:00Z")]
    selected, _ = index.resolve("0001",early)
    assert index.available(selected,late)
    assert not index.continuous(selected,early,late)
