from app.errors import FieldError
from app.manifest import canonical, identify, json_sha
from app.modules.intake.catalog import restore


def verify(archive):
    manifest, evidence, source = archive
    package = restore(source)
    identity, hashes = identify(package, manifest["policy"])
    if (identity != manifest["id"] or hashes != manifest["hashes"] or json_sha(evidence) != manifest["result_sha256"]):
        raise FieldError("ARCHIVE_DAMAGED", "归卷摘要不符", 409)
    return package


def export(archive):
    verify(archive)
    manifest, evidence, source = archive
    return canonical({"format": "museum-cabinet-evidence-v1", "manifest": manifest,
                      "input": source, "evidence": evidence}).encode("utf-8")
