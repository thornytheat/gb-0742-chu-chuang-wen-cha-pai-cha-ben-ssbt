from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.dependencies import Archive, Service
from app.modules.archive.proof import export

router = APIRouter(prefix="/api/runs")


class RunRequest(BaseModel):
    sample: str


@router.get("")
def history(service: Service):
    return service.store.history()


@router.post("", status_code=201)
def run(body: RunRequest, service: Service, response: Response):
    result = service.run(body.sample)
    if result["reused"]:
        response.status_code = 200
    return result


@router.get("/{run_id}")
def manifest(archive: Archive):
    return archive[0]


@router.post("/{run_id}/rerun")
def replay(run_id: str, service: Service):
    return service.replay(run_id)


@router.get("/{run_id}/export")
def evidence(archive: Archive):
    filename = f'museum-{archive[0]["id"][:16]}.json'
    return Response(export(archive), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
