from fastapi import APIRouter

from app.dependencies import Archive

router = APIRouter(prefix="/api/runs/{run_id}")


@router.get("/audit")
def reconciliation(archive: Archive):
    return {**archive[1]["audit"], "isolation": archive[1]["isolation"]}
