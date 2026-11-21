from fastapi import APIRouter

from app.dependencies import Archive, query_time
from app.modules.assignment.windows import DeploymentIndex
from app.modules.intake.contract import Shift

router = APIRouter(prefix="/api/runs/{run_id}/assignment")


@router.get("")
def assignments(archive: Archive):
    snapshot = archive[1]
    return {"windows": snapshot["deployments"], "conflicts": snapshot["deployment_conflicts"],
            "issues": [row for row in snapshot["rows"] if row["code"] in {"NO_DEPLOYMENT", "DEPLOYMENT_CONFLICT", "OFF_SHIFT"}],
            "late": [row for row in snapshot["rows"] if "LATE_RECEIPT" in row.get("flags", [])]}


@router.get("/lookup")
def lookup(archive: Archive, probe: str, at: str):
    spec = Shift.model_validate(archive[2]["contract"])
    window, reason = DeploymentIndex(spec).resolve(probe, query_time(at))
    return {"deployment": window, "code": reason}
