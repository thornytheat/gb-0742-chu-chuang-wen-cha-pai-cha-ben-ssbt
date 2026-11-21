from app.modules.audit.reconcile import reconcile


def test_expected_cabinet_hours_conserved_with_gaps(snapshot):
    assert snapshot["audit"]["hours"] == {"expected":20,"stable":11,"abnormal":5,"missing":4,"balanced":True,
                                            "missing_keys":[],"extra_keys":[],"duplicate_keys":[]}


def test_reconciliation_catches_substituted_slot_even_if_total_matches(package,snapshot):
    actual = [*snapshot["grades"][1:],snapshot["grades"][1]]
    audit = reconcile(package.spec,snapshot["rows"],snapshot["intake"],actual,snapshot["episodes"])
    assert not audit["hours"]["balanced"]
    assert audit["hours"]["missing_keys"] == [["CV-17","2026-11-20T00:00:00Z"]]
    assert audit["hours"]["duplicate_keys"] == [["CV-17","2026-11-20T01:00:00Z"]]


def test_raw_records_partition_dedup_exceptions_and_layout(snapshot):
    assert snapshot["audit"]["row_audit"] == {"total":54,"declared":52,"accepted":41,"isolated":10,"duplicate":1,
                                                "blank":1,"header":1,"balanced":True}
    assert len({row["id"] for row in snapshot["rows"]}) == 54


def test_ticket_can_only_clear_one_sustained_episode_and_other_is_unreported(snapshot):
    audit = snapshot["audit"]
    assert [(row["id"],row["code"],row["episode"]) for row in audit["tickets"][:2]] == [
        ("AL-0701","MATCHED","CV-17-A01"),("AL-0702","DUPLICATE_ALARM","CV-17-A01")]
    assert audit["unreported"] == ["CV-17-A03"]
    assert audit["tickets"][0]["evidence"] == ["night-points.csv:6","night-points.csv:8"]


def test_ticket_boundary_assigns_missing_hour_not_previous_episode(snapshot):
    report = snapshot["audit"]["tickets"][2]
    assert report["slot"] == "2026-11-20T03:00:00Z"
    assert report["code"] == "MISSING_EVIDENCE" and report["episode"] is None
    end = snapshot["audit"]["tickets"][-1]
    assert (end["code"],end["evidence"]) == ("OUTSIDE_SHIFT",[])


def test_api_gives_ticket_codes_and_actual_unreported_episode(client,base):
    result = client.get(base + "/audit").json()
    assert result["ticket_counts"] == {"DUPLICATE_ALARM":1,"MATCHED":1,"MISSING_EVIDENCE":1,"OUTSIDE_SHIFT":1,
                                 "STABLE_AT_ALARM":1,"TRANSIENT_ONLY":1,"UNKNOWN_CABINET":1}
    assert result["unreported"] == ["CV-17-A03"]
    assert sum(result["isolation"].values()) == 10
