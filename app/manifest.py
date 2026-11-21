import base64
import hashlib
import json

from app.config import POLICY


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_sha(data):
    return sha(canonical(data).encode("utf-8"))


def identify(package, policy=POLICY):
    hashes = {"file_sha256": sha(package.blob), "contract_sha256": json_sha(package.spec.model_dump(mode="json"))}
    return json_sha([policy, hashes]), hashes


def preserve(package):
    return {"contract": package.spec.model_dump(mode="json"), "csv_base64": base64.b64encode(package.blob).decode("ascii")}
