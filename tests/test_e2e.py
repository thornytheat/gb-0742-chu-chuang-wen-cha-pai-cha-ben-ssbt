from fastapi.testclient import TestClient

from app.main import create_app


def test_seven_business_entrances_and_replay_with_real_fixture(client,base):
    cases = {"/intake":"rows","/assignment":"windows","/pairing/CV-17":"slots","/gradient/CV-17":"slots",
             "/episodes/CV-17/CV-17-A03":"rows","/audit":"tickets","":"hashes","/export":"manifest"}
    for name, key in cases.items():
        live = client.get(base + name)
        assert live.status_code == 200 and live.json()[key], name
    assert client.post(base + "/rerun").json()["verified"]


def test_all_pages_render_expected_heading_navigation_and_controls(client):
    pages = {"/":"垂直梯度","/intake":"点位采信","/assignment":"探头迁移","/pairing":"时窗配准",
             "/episodes":"异常持续","/audit":"值班单勾稽","/archive":"证据归卷"}
    for path, name in pages.items():
        page = client.get(path)
        assert page.status_code == 200
        assert f"<h1>{name}</h1>" in page.text
        assert 'id="print"' in page.text and 'class="footnotes"' in page.text
    assert client.get("/static/main.js").status_code == 200
    assert "@media print" in client.get("/static/layout.css").text


def test_clean_sample_passes_all_hours_and_has_empty_episode_list(client):
    result = client.post("/api/runs",json={"sample":"clean"}).json()
    base = f'/api/runs/{result["manifest"]["id"]}'
    hours = client.get(base + "/audit").json()["hours"]
    assert (hours["expected"],hours["stable"],hours["abnormal"],hours["missing"]) == (3,3,0,0)
    assert client.get(base + "/episodes/CV-17").json() == []


def test_first_start_is_seeded_and_restart_uses_saved_archive(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    with TestClient(create_app(path)) as first:
        records = first.get("/api/runs").json()
        assert len(records) == 1 and records[0]["shift"] == "N26-1120"
    with TestClient(create_app(path)) as second:
        assert second.get("/api/runs").json() == records


def test_unknown_cabinet_run_and_sample_are_distinct(client,base):
    failures = [client.get(base + "/pairing/CV-99"),client.get("/api/runs/notfound"),client.post("/api/runs",json={"sample":"bad"})]
    for result,code in zip(failures,["UNKNOWN_CABINET","UNKNOWN_RUN","UNKNOWN_SAMPLE"]):
        assert (result.status_code,result.json()["code"]) == (404,code)
