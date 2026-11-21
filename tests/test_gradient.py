from copy import deepcopy
from decimal import Decimal

from app.modules.gradient.grade import grade
from app.modules.gradient.interval import confidence


def test_confidence_uses_uncertainty_and_real_sensor_height(snapshot):
    slot = snapshot["grades"][0]
    assert slot["gap_mm"] == 1000
    assert slot["temperature"] == {"value":"1.500","low":"1.223","high":"1.777","limit":"2.0","verdict":"STABLE"}
    second_cabinet = snapshot["grades"][10]
    assert second_cabinet["gap_mm"] == 1200
    assert second_cabinet["temperature"]["value"] == "0.417"


def test_gradient_compares_unrounded_endpoints():
    # Positive lower bound is barely above threshold even though it displays 2.000.
    report = confidence(["2.2773","0.1000"],["0","0.1000"],1000,Decimal("2"))
    assert report["low"] == "2.000" and report["verdict"] == "ABNORMAL"
    nearby = confidence(["2.2771","0.1000"],["0","0.1000"],1000,Decimal("2"))
    assert nearby["low"] == "2.000" and nearby["verdict"] == "UNCERTAIN"


def test_negative_interval_can_be_certainly_abnormal(snapshot):
    slot = snapshot["grades"][4]
    assert slot["temperature"]["high"] == "-2.723"
    assert (slot["state"],slot["axes"]) == ("ABNORMAL",["temperature"])


def test_overlapping_threshold_is_missing_not_an_alarm(snapshot):
    slot = snapshot["grades"][3]
    assert slot["temperature"]["value"] == "2.000"
    assert slot["temperature"]["verdict"] == "UNCERTAIN"
    assert (slot["state"],slot["code"]) == ("MISSING","CI_OVERLAP")


def test_humidity_can_drive_grade_while_temperature_is_safe(snapshot):
    slot = snapshot["grades"][7]
    assert slot["temperature"]["verdict"] == "STABLE"
    assert slot["humidity"]["low"] == "14.446"
    assert (slot["state"],slot["axes"]) == ("ABNORMAL",["humidity"])


def test_missing_humidity_cannot_prove_joint_stability(package,snapshot):
    rows = deepcopy(snapshot["rows"])
    rows[0]["relative_humidity"] = None
    result = grade(package.spec,snapshot["pairs"][:1],rows)[0]
    assert result["temperature"]["verdict"] == "STABLE"
    assert result["humidity"] is None
    assert (result["state"],result["code"]) == ("MISSING","MISSING_RH")


def test_evidence_returns_exact_two_raw_rows_for_cabinet_hour(client,base):
    url = base + "/gradient/CV-17/evidence"
    reply = client.get(url,params={"at":"2026-11-20T09:00:00+08:00"})
    assert reply.status_code == 200
    assert {row["id"] for row in reply.json()["rows"]} == {"night-points.csv:6","night-points.csv:8"}
    missing = client.get(url,params={"at":"2026-11-20T09:02:00+08:00"})
    assert (missing.status_code,missing.json()["code"]) == (404,"UNKNOWN_SLOT")
