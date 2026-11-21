from fastapi import APIRouter

from app.dependencies import Archive
from app.modules.intake.catalog import CATALOG

router = APIRouter(prefix="/api")


@router.get("/samples")
def samples():
    return [{"id": key, "label": name} for key, name in CATALOG.items()]


@router.get("/runs/{run_id}/intake")
def intake(archive: Archive):
    _, snapshot, _ = archive
    return {**snapshot["intake"], "rows": snapshot["rows"], "isolation": snapshot["isolation"]}
