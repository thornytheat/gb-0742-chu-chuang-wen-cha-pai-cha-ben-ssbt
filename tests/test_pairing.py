from app.modules.assignment.windows import DeploymentIndex
from app.modules.pairing.matching import optimal_matching
from app.timebase import seconds


def points(times, window):
    return [{"measured":moment, "deployment":window} for moment in times]


def test_assignment_maximizes_pairs_before_distance(package):
    index = DeploymentIndex(package.spec)
    origin = seconds(package.spec.start)
    upper = points([origin+100,origin+106],index.windows[0])
    lower = points([origin+96,origin+101],index.windows[2])
    assert optimal_matching([[row] for row in upper], lower, 5, index) == ({0:(0,0),1:(0,1)},{0,1})


def test_no_lower_reuse_even_when_two_slots_both_can_use_it(package):
    index = DeploymentIndex(package.spec)
    origin = seconds(package.spec.start)
    upper = points([origin+3599,origin+3602],index.windows[0])
    lower = points([origin+3601],index.windows[2])
    assert optimal_matching([[row] for row in upper],lower,5,index) == ({1:(0,0)},{0,1})


def test_tolerance_includes_exact_boundary(package):
    index = DeploymentIndex(package.spec)
    origin = seconds(package.spec.start)
    upper = points([origin+600],index.windows[0])
    lower = points([origin+840],index.windows[2])
    assert optimal_matching([upper],lower,240,index) == ({0:(0,0)},{0})
    assert optimal_matching([upper],lower,239,index) == ({},set())


def test_migration_forbids_closer_cross_boundary_reading(snapshot):
    paired = next(slot for slot in snapshot["pairs"] if slot["cabinet"] == "CV-17" and "T05:00" in slot["start"])
    assert (paired["upper"],paired["lower"],paired["drift"]) == ("night-points.csv:25","night-points.csv:26",180)
    assert any(row["id"] == "night-points.csv:46" for row in snapshot["unused"])


def test_picks_lower_with_minimum_drift_and_preserves_unused(snapshot):
    slot = next(row for row in snapshot["pairs"] if row["cabinet"] == "CV-21" and "T07:00" in row["start"])
    assert (slot["lower"],slot["drift"]) == ("night-points.csv:36",60)
    assert {"id":"night-points.csv:47","code":"UNUSED_LOWER","cabinet":"CV-21"} in snapshot["unused"]


def test_no_pair_and_no_upper_are_separate_states(snapshot):
    slots = [slot for slot in snapshot["pairs"] if slot["cabinet"] == "CV-17"]
    assert (slots[6]["upper"],slots[6]["code"]) == ("night-points.csv:29","NO_COMPATIBLE_LOWER")
    assert (slots[9]["upper"],slots[9]["code"]) == (None,"MISSING_UPPER")


def test_window_contention_records_explicit_missing_state(package):
    from app.modules.pairing.schedule import schedule

    index = DeploymentIndex(package.spec)
    origin = seconds(package.spec.start)
    rows = [{"id":f"row{n}","disposition":"accepted","line":n, **data} for n,data in enumerate(
        points([origin+3599,origin+3602],index.windows[0])+points([origin+3601],index.windows[2]),1)]
    slots,_ = schedule(package.spec,rows,index)
    assert (slots[0]["code"],slots[1]["lower"],slots[1]["drift"]) == ("LOWER_CONTENTION","row3",1)


def test_all_upper_readings_compete_before_selecting_hourly_evidence(snapshot):
    first = snapshot["pairs"][0]
    assert (first["upper"],first["lower"],first["drift"]) == ("night-points.csv:2","night-points.csv:3",120)
    extra = next(row for row in snapshot["rows"] if row["id"] == "night-points.csv:56")
    assert extra["observed_utc"] == "2026-11-20T00:29:00Z"
    assert {"id":extra["id"],"code":"EXTRA_UPPER","cabinet":"CV-17"} in snapshot["unused"]


def test_chooses_closest_of_multiple_eligible_upper_readings(package):
    index = DeploymentIndex(package.spec)
    origin = seconds(package.spec.start)
    uppers = points([origin+603,origin+600],index.windows[0])
    lowers = points([origin+600],index.windows[2])
    assert optimal_matching([uppers],lowers,5,index) == ({0:(1,0)},{0})
