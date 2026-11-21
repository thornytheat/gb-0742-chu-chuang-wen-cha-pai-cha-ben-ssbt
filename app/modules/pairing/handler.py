from fastapi import APIRouter

from app.dependencies import Archive, cabinet_scope

router = APIRouter(prefix="/api/runs/{run_id}")


@router.get("/pairing/{cabinet}")
def pairs(archive: Archive, cabinet: str):
    manifest, snapshot, _ = archive
    cabinet_scope(manifest, cabinet)
    return {"tolerance_seconds": manifest["tolerance_seconds"],
            "slots": [slot for slot in snapshot["pairs"] if slot["cabinet"] == cabinet],
            "unused": [row for row in snapshot["unused"] if row["cabinet"] == cabinet]}
