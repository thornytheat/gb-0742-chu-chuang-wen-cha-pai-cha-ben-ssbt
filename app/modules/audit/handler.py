from fastapi import APIRouter

from app.dependencies import Archive

router = APIRouter(prefix="/api/runs/{run_id}")


@router.get("/audit")
def reconciliation(archive: Archive):
    return {**archive[1]["audit"], "isolation": archive[1]["isolation"]}


@router.get("/claims")
def claims(archive: Archive):
    audit = archive[1]["audit"]
    return {"claims": audit["claims"], "summary": audit["claim_summary"], "tickets": audit["tickets"]}
