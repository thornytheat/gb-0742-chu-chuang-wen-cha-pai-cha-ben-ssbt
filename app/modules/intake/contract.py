from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.timebase import seconds

IDENT = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,32}$")]


class Window(BaseModel):
    start: str
    end: str

    @model_validator(mode="after")
    def ordered(self):
        if seconds(self.start) >= seconds(self.end):
            raise ValueError("时窗结束须晚于开始")
        return self


class Cabinet(BaseModel):
    id: IDENT
    label: str
    upper_mm: int = Field(ge=150, le=5000)
    lower_mm: int = Field(ge=0, le=4500)
    temp_limit: Decimal = Field(gt=0, le=20)
    rh_limit: Decimal = Field(gt=0, le=100)

    @model_validator(mode="after")
    def valid_separation(self):
        if self.upper_mm - self.lower_mm < 100:
            raise ValueError("上下探头须相隔至少 100 mm")
        return self


class Deployment(Window):
    probe: IDENT
    cabinet: IDENT
    level: Literal["upper", "lower"]


class Ticket(BaseModel):
    id: IDENT
    cabinet: IDENT
    at: str
    status: Literal["ACTIVE", "CANCELLED"] = "ACTIVE"
    arrived: str | None = None
    note: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data):
        """Accept the ticket spellings used by older handover exports.

        Only unambiguous aliases are translated; any other status is rejected
        rather than guessed, because mistaking an open ticket for a handled one
        would wrongly close an episode.
        """
        if not isinstance(data, dict):
            return data
        data = dict(data)
        for alias in ("arrived_at", "arrival", "arrival_at", "on_site"):
            if alias in data and data.get("arrived") is None:
                data["arrived"] = data.pop(alias)
        if "state" in data and "status" not in data:
            data["status"] = data.pop("state")
        for alias in ("cancelled", "canceled", "void", "revoked"):
            if alias in data and "status" not in data:
                flag = data.pop(alias)
                if isinstance(flag, str):
                    flag = flag.strip().lower() in {"1", "true", "yes", "y", "是", "撤销", "已撤销"}
                data["status"] = "CANCELLED" if flag else "ACTIVE"
        status = data.get("status")
        if isinstance(status, str):
            token = status.strip().upper()
            data["status"] = {"CANCELED": "CANCELLED", "撤销": "CANCELLED",
                              "已撤销": "CANCELLED", "作废": "CANCELLED",
                              "VOID": "CANCELLED", "REVOKED": "CANCELLED"}.get(token, token)
        return data

    @model_validator(mode="after")
    def valid_time(self):
        alarm = seconds(self.at)
        if self.arrived is not None and seconds(self.arrived) < alarm:
            raise ValueError("到场时刻不能早于报警")
        return self


class Shift(Window):
    cabinet_hours: list[Cabinet] = Field(min_length=1, max_length=8)
    sample: IDENT
    label: str
    shift: IDENT
    csv: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,30}\.csv$")]
    records: int = Field(ge=1, le=4000)
    tolerance_seconds: int = Field(ge=0, le=900)
    late_seconds: int = Field(ge=0, le=86_400)
    sustained_hours: int = Field(ge=2, le=12)
    deployments: list[Deployment] = Field(min_length=1, max_length=64)
    tickets: list[Ticket] = Field(max_length=100)

    @model_validator(mode="after")
    def check_shift(self):
        duration = seconds(self.end) - seconds(self.start)
        if not (0 < duration <= 168 * 3600) or duration % 3600 or seconds(self.start) % 3600:
            raise ValueError("班次使用整点小时，最长七天")
        cabinets = {item.id for item in self.cabinet_hours}
        if len(cabinets) != len(self.cabinet_hours):
            raise ValueError("柜号重复")
        if any(item.cabinet not in cabinets for item in self.deployments):
            raise ValueError("部署柜未登记")
        if len({item.id for item in self.tickets}) != len(self.tickets):
            raise ValueError("工单号重复")
        return self


@dataclass(frozen=True)
class Package:
    spec: Shift
    blob: bytes
