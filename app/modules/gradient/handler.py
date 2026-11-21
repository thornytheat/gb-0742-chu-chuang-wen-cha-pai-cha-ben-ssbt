from fastapi import APIRouter

from app.dependencies import Archive, cabinet_scope, query_time
from app.errors import FieldError

router = APIRouter(prefix="/api/runs/{run_id}/gradient/{cabinet}")


@router.get("")
def grades(archive: Archive, cabinet: str):
    spec = cabinet_scope(archive[0], cabinet)
    return {"cabinet": spec, "slots": [slot for slot in archive[1]["grades"] if slot["cabinet"] == cabinet]}


@router.get("/evidence")
def proof(archive: Archive, cabinet: str, at: str):
    spec = cabinet_scope(archive[0], cabinet)
    snapshot = archive[1]
    hour = query_time(at)
    slot = next((item for item in snapshot["grades"] if item["cabinet"] == cabinet and item["hour"] == hour), None)
    if slot is None:
        raise FieldError("UNKNOWN_SLOT", "柜时未登记，请选择整点", 404)
    ids = {slot["upper"], slot["lower"]}
    return {"cabinet": spec, "slot": slot, "rows": [row for row in snapshot["rows"] if row["id"] in ids]}
