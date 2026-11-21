from app.modules.episodes.segment import segment


def test_episode_splits_at_unknown_link_between_abnormal_hours(snapshot):
    groups = snapshot["episodes"]
    assert [(row["start"][11:16],row["end"][11:16],row["kind"]) for row in groups] == [
        ("01:00","03:00","SUSTAINED"),("04:00","05:00","TRANSIENT"),("07:00","09:00","SUSTAINED")]


def test_episode_duration_and_axis_summary_match_each_slot(snapshot):
    groups = snapshot["episodes"]
    assert [item["hours"] for item in groups] == [2,1,2]
    assert [item["axes"] for item in groups] == [["temperature"],["temperature"],["humidity"]]
    traced = {(group["cabinet"],row["start"]) for group in groups for row in group["evidence"]}
    assert traced == {(slot["cabinet"],slot["start"]) for slot in snapshot["grades"] if slot["state"] == "ABNORMAL"}


def test_sustained_threshold_is_inclusive_and_configurable(snapshot):
    assert sum(item["kind"] == "SUSTAINED" for item in segment(snapshot["grades"],2)) == 2
    assert sum(item["kind"] == "SUSTAINED" for item in segment(snapshot["grades"],3)) == 0


def test_unsorted_input_preserves_groups_and_evidence(snapshot):
    assert segment(list(reversed(snapshot["grades"])),2) == snapshot["episodes"]


def test_two_cabinets_do_not_join_contiguous_hours(snapshot):
    g = snapshot["grades"]
    rows = [g[1], {**g[2],"cabinet":"CV-21"}]
    assert [(item["id"],item["hours"]) for item in segment(rows,2)] == [("CV-17-A01",1),("CV-21-A01",1)]


def test_episode_detail_has_all_four_rows_and_unknown_segment_is_404(client,base):
    url = base + "/episodes/CV-17"
    episode = client.get(url + "/CV-17-A01").json()
    assert episode["kind"] == "SUSTAINED" and len(episode["rows"]) == 4
    assert {row["id"] for row in episode["rows"]} == {"night-points.csv:6","night-points.csv:8","night-points.csv:11","night-points.csv:12"}
    response = client.get(url + "/CV-17-A80")
    assert (response.status_code,response.json()["code"]) == (404,"UNKNOWN_EPISODE")
