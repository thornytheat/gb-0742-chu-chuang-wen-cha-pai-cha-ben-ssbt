from typing import Annotated

from fastapi import Depends, Request

from app.errors import FieldError
from app.modules.archive.service import ArchiveService
from app.timebase import seconds


def service(request: Request):
    return request.app.state.archives


def archive(run_id: str, request: Request):
    return service(request).store.fetch(run_id)


Archive = Annotated[tuple, Depends(archive)]
Service = Annotated[ArchiveService, Depends(service)]


def cabinet_scope(manifest, cabinet):
    if cabinet is None:
        return None
    for item in manifest["cabinets"]:
        if item["id"] == cabinet:
            return item
    raise FieldError("UNKNOWN_CABINET", "展柜未登记", 404)


def query_time(value):
    try:
        return seconds(value)
    except (ValueError, OverflowError, OSError) as exc:
        raise FieldError("BAD_TIME", "请输入带偏移的整秒时间") from exc
