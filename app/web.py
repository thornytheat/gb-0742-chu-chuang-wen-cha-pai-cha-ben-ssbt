from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import ROOT

router = APIRouter()
templates = Jinja2Templates(directory=ROOT / "app/templates")
STAGES = {
    "intake": ("点位采信", "/intake"), "assignment": ("探头迁移", "/assignment"),
    "pairing": ("时窗配准", "/pairing"), "gradient": ("垂直梯度", "/"),
    "episodes": ("异常持续", "/episodes"), "audit": ("值班单勾稽", "/audit"), "archive": ("证据归卷", "/archive"),
}


@router.get("/healthz", include_in_schema=False)
def health():
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/intake", response_class=HTMLResponse, include_in_schema=False)
@router.get("/assignment", response_class=HTMLResponse, include_in_schema=False)
@router.get("/pairing", response_class=HTMLResponse, include_in_schema=False)
@router.get("/episodes", response_class=HTMLResponse, include_in_schema=False)
@router.get("/audit", response_class=HTMLResponse, include_in_schema=False)
@router.get("/archive", response_class=HTMLResponse, include_in_schema=False)
def workbench(request: Request):
    stage = request.url.path.strip("/") or "gradient"
    return templates.TemplateResponse(request, "base.html", {"stage": stage, "stages": STAGES})
