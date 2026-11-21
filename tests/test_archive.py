import base64
from concurrent.futures import ThreadPoolExecutor

from app.manifest import identify, json_sha, sha
from app.modules.archive.service import ArchiveService
from app.modules.intake.contract import Package


def test_same_input_reuses_manifest_and_does_not_duplicate_history(client,base):
    manifest = client.get(base).json()
    again = client.post("/api/runs",json={"sample":"shift"})
    assert again.status_code == 200 and again.json() == {"manifest":manifest,"reused":True}
    assert client.get("/api/runs").json() == [manifest]


def test_replay_reads_pinned_input_and_keeps_digest(client,base):
    manifest = client.get(base).json()
    service = ArchiveService(client.app.state.archives.store, loader=lambda _: None)
    assert service.replay(manifest["id"]) == {"manifest":manifest,"reused":True,"verified":True}
    assert len(service.store.history()) == 1


def test_concurrent_duplicate_submission_writes_only_one_row(client):
    service = client.app.state.archives
    with ThreadPoolExecutor(max_workers=5) as pool:
        outcomes = list(pool.map(service.run,["shift"]*5))
    assert sum(not item["reused"] for item in outcomes) == 1
    assert all(item["manifest"] == outcomes[0]["manifest"] for item in outcomes)
    assert len(service.store.history()) == 1


def test_truncation_aborts_archive_without_touching_existing_run(client,base):
    # TRAP-16
    prior = client.get(base).json()
    reply = client.post("/api/runs",json={"sample":"truncated"})
    assert (reply.status_code,reply.json()["code"]) == (422,"TRUNCATED_INPUT")
    assert "声明 6 条，实收 2 条" in reply.json()["message"]
    assert client.get("/api/runs").json() == [prior]


def test_sqlite_failure_is_rolled_back_and_recoverable(client,base):
    store = client.app.state.archives.store
    with store.connect() as db:
        db.execute("CREATE TRIGGER injected AFTER INSERT ON shift_archives BEGIN SELECT RAISE(ABORT, 'disk'); END")
    failed = client.post("/api/runs",json={"sample":"clean"})
    assert (failed.status_code,failed.json()["code"]) == (503,"ARCHIVE_UNAVAILABLE")
    assert len(store.history()) == 1
    with store.connect() as db:
        db.execute("DROP TRIGGER injected")
    assert client.post("/api/runs",json={"sample":"clean"}).status_code == 201
    assert len(store.history()) == 2


def test_downloaded_evidence_is_self_verifiable_and_byte_stable(client,base,package):
    delivery = client.get(base + "/export")
    item = delivery.json()
    assert item["format"] == "museum-cabinet-evidence-v1"
    assert delivery.headers["content-disposition"].startswith('attachment; filename="museum-')
    assert base64.b64decode(item["input"]["csv_base64"]) == package.blob
    assert item["manifest"]["hashes"]["file_sha256"] == sha(package.blob)
    assert item["manifest"]["result_sha256"] == json_sha(item["evidence"])
    assert client.get(base + "/export").content == delivery.content


def test_tampered_evidence_refuses_replay_and_export(client,base):
    service = client.app.state.archives
    with service.store.connect() as db:
        db.execute("UPDATE shift_archives SET evidence = '{}' WHERE id = ?",(base.rsplit('/',1)[1],))
    for error in [client.post(base + "/rerun"),client.get(base + "/export")]:
        assert (error.status_code,error.json()["code"]) == (409,"ARCHIVE_DAMAGED")


def test_identity_changes_on_policy_content_or_time_tolerance(package):
    modified = package.spec.model_copy(update={"tolerance_seconds":235})
    keys = {identify(package)[0],identify(package,"v2")[0],identify(Package(modified,package.blob))[0],
            identify(Package(package.spec,package.blob+b"\n"))[0]}
    assert len(keys) == 4
