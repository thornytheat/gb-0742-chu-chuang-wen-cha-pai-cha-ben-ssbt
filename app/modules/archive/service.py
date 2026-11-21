from datetime import datetime, timezone
from time import perf_counter

from app.config import POLICY
from app.errors import FieldError
from app.manifest import identify, json_sha, preserve
from app.modules.archive.pipeline import evaluate
from app.modules.archive.proof import verify
from app.modules.intake.catalog import load_sample
from app.timebase import seconds, utc


class ArchiveService:
    def __init__(self, store, loader=load_sample):
        self.store = store
        self.loader = loader

    def run(self, sample):
        start = perf_counter()
        package = self.loader(sample)
        evidence = evaluate(package)
        spec = package.spec
        key, hashes = identify(package)
        manifest = {"id": key, "sample": spec.sample, "label": spec.label, "shift": spec.shift, "policy": POLICY,
                    "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "window": [utc(seconds(spec.start)), utc(seconds(spec.end))],
                    "cabinets": [cabinet.model_dump(mode="json") for cabinet in spec.cabinet_hours],
                    "tolerance_seconds": spec.tolerance_seconds, "sustained_hours": spec.sustained_hours,
                    "file": spec.csv, "hashes": hashes, "result_sha256": json_sha(evidence),
                    "elapsed_ms": round(1000 * (perf_counter() - start)), "summary": evidence["audit"]["hours"]}
        record, created = self.store.insert(manifest, evidence, preserve(package))
        if record["result_sha256"] != manifest["result_sha256"]:
            raise FieldError("RULE_DRIFT", "同版结果摘要不一致", 409)
        return {"manifest": record, "reused": not created}

    def replay(self, run_id):
        archive = self.store.fetch(run_id)
        manifest = archive[0]
        if manifest["policy"] != POLICY:
            raise FieldError("OLD_POLICY", "当前规则无法复算此归卷", 409)
        pinned = verify(archive)
        if json_sha(evaluate(pinned)) != manifest["result_sha256"]:
            raise FieldError("RULE_DRIFT", "复算结果摘要不一致", 409)
        return {"manifest": manifest, "verified": True, "reused": True}
