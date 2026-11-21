import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.config import ROOT, database_path
from app.errors import FieldError
from app.modules.archive import handler as archive
from app.modules.archive.service import ArchiveService
from app.modules.assignment import handler as assignment
from app.modules.audit import handler as audit
from app.modules.episodes import handler as episodes
from app.modules.gradient import handler as gradient
from app.modules.intake import handler as intake
from app.modules.pairing import handler as pairing
from app.store import ArchiveStore
from app.web import router as web


def create_app(path=None, seed=True):
    @asynccontextmanager
    async def lifespan(app):
        await run_in_threadpool(app.state.archives.store.setup)
        if seed and not await run_in_threadpool(app.state.archives.store.history):
            await run_in_threadpool(app.state.archives.run, "shift")
        yield

    app = FastAPI(title="橱窗温差排查本", lifespan=lifespan)
    app.state.archives = ArchiveService(ArchiveStore(path or database_path()))
    app.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")
    for module in (intake, assignment, pairing, gradient, episodes, audit, archive):
        app.include_router(module.router)
    app.include_router(web)
    app.add_exception_handler(FieldError, domain_error)
    app.add_exception_handler(sqlite3.Error, storage_error)
    return app


async def domain_error(request: Request, exc: FieldError):
    return JSONResponse({"code": exc.code, "message": str(exc)}, status_code=exc.status)


async def storage_error(request: Request, exc: sqlite3.Error):
    return JSONResponse({"code": "ARCHIVE_UNAVAILABLE", "归卷信息": "暂未写入", "message": "归卷暂不可用，请重试"}, status_code=503)


app = create_app()
