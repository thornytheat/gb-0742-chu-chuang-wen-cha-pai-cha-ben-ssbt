from datetime import datetime, timezone


def seconds(value):
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None or moment.microsecond != 0:
        raise ValueError("时间需包含偏移和整秒")
    try:
        return int(moment.astimezone(timezone.utc).timestamp())
    except (OverflowError, OSError) as exc:
        raise ValueError("UTC 时间超出支持范围") from exc


def utc(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
