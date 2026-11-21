from fastapi import APIRouter

from app.dependencies import Archive, cabinet_scope
from app.errors import FieldError

router = APIRouter(prefix="/api/runs/{run_id}/episodes")


@router.get("/{cabinet}")
def episodes(archive: Archive, cabinet: str):
    cabinet_scope(archive[0], cabinet)
    return [item for item in archive[1]["episodes"] if item["cabinet"] == cabinet]


@router.get("/{cabinet}/{episode_id}")
def episode(archive: Archive, cabinet: str, episode_id: str):
    for item in episodes(archive, cabinet):
        if item["id"] == episode_id:
            ids = {row[level] for row in item["evidence"] for level in ("upper", "lower")}
            return {**item, "rows": [row for row in archive[1]["rows"] if row["id"] in ids]}
    raise FieldError("UNKNOWN_EPISODE", "异常段未登记", 404)
