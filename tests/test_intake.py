from app.modules.archive.pipeline import evaluate
from app.modules.intake.catalog import load_sample
from app.modules.intake.values import parse_measurement


def test_real_encodings_and_bom(snapshot):
    # TRAP-01, TRAP-02
    clean = evaluate(load_sample("clean"))
    assert clean["intake"]["encoding"] == "gb18030"
    assert clean["rows"][0]["fields"]["memo"] == "库房校验"
    assert snapshot["intake"] == {"encoding":"utf-8-sig","segments":2,"declared":52,"physical":56}


def test_multiline_note_keeps_source_span_and_text(snapshot):
    # TRAP-03
    row = snapshot["rows"][4]
    assert (row["id"], row["end_line"]) == ("night-points.csv:6", 7)
    assert row["fields"]["memo"] == "北侧玻璃, 夜班交接\n复核挂签"


def test_header_switch_changes_field_positions(snapshot):
    # TRAP-04, TRAP-17
    row = next(row for row in snapshot["rows"] if row["id"] == "night-points.csv:25")
    assert row["raw"][1] == row["fields"]["received"]
    assert row["raw"][2] == row["fields"]["observed"]
    assert [row["code"] for row in snapshot["rows"]].count("HEADER_REPEAT") == 1


def test_wrong_width_retains_last_extra_field(snapshot):
    # TRAP-05
    row = next(row for row in snapshot["rows"] if row["code"] == "WRONG_WIDTH")
    assert (row["line"],row["code"],row["raw"][-1],row["disposition"]) == (55,"WRONG_WIDTH","多列","isolated")


def test_fahrenheit_uncertainty_and_humidity_ratios_normalize_before_dedup(snapshot):
    # TRAP-06, TRAP-11, TRAP-15
    original = snapshot["rows"][0]
    duplicate = next(row for row in snapshot["rows"] if row["code"] == "DUPLICATE_READING")
    assert duplicate["fields"]["temp"] == "７０.７"
    assert duplicate["observed_utc"] == original["observed_utc"] == "2026-11-20T00:10:00Z"
    assert duplicate["celsius"] == original["celsius"] == ["21.5000","0.1000"]
    assert duplicate["relative_humidity"] == original["relative_humidity"] == ["50.0000","0.2000"]
    assert duplicate["delay"] > original["delay"]


def test_probe_id_keeps_leading_zeros(snapshot):
    # TRAP-08
    row = snapshot["rows"][0]
    assert row["probe"] == row["deployment"]["probe"] == "0001"


def test_conflicting_same_probe_same_second_is_quarantined_jointly(snapshot):
    # TRAP-14
    conflicts = [row for row in snapshot["rows"] if row["code"] == "READING_CONFLICT"]
    assert len(conflicts) == 2
    assert {(row["probe"],row["observed_utc"]) for row in conflicts} == {("0008","2026-11-20T01:11:00Z")}
    assert {row["celsius"][0] for row in conflicts} == {"21.5000","28.0000"}
    assert all("deployment" not in row for row in conflicts)


def test_no_temperature_is_distinct_from_other_bad_measurements(snapshot):
    # TRAP-07
    codes = {row["code"]:row for row in snapshot["rows"] if row["code"] in {"NO_TEMPERATURE","BAD_TIME","BAD_UNIT","BAD_READING","RECEIPT_BEFORE_MEASURE"}}
    assert len(codes) == 5
    assert codes["NO_TEMPERATURE"]["fields"]["temp"] == "N/A"
    assert codes["BAD_READING"]["fields"]["temp_sigma"] == "0"


def test_signed_zero_and_freezing_fahrenheit_share_normalized_values(snapshot):
    fields = {**snapshot["rows"][0]["fields"], "rh": "-0"}
    first = {"fields": dict(fields, temp="-0")}
    second = {"fields": dict(fields, temp="32", temp_unit="F", temp_sigma=".18")}
    for row in (first, second):
        parse_measurement(row, 900)
    assert first["celsius"] == second["celsius"] == ["0.0000", "0.1000"]
    assert first["relative_humidity"] == second["relative_humidity"] == ["0.0000", "0.2000"]
