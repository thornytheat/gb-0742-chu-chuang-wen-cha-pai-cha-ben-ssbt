import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.reasons import mark
from app.timebase import seconds, utc

NULLS = {"", "-", "N/A", "NULL", "未知"}
TEMP_SCALE = {"C": (0,1,1), "F": (32,5,9), "K": (Decimal("273.15"),1,1)}
RH_SCALE = {"PCT": 1, "%": 1, "RATIO": 100}


def normalize(value):
    return unicodedata.normalize("NFKC", value).strip().upper()


def decimal(value):
    token = normalize(value)
    if not re.fullmatch(r"[+-]?(?:[0-9]{1,6}(?:\.[0-9]{1,6})?|\.[0-9]{1,6})", token):
        raise InvalidOperation
    return Decimal(token)


def scaled(value, sigma, offset, multiplier, divisor, low, high, max_sigma):
    quant = Decimal("0.0001")
    amount = (decimal(value) - offset) * multiplier / divisor
    deviation = (decimal(sigma) * multiplier / divisor).quantize(quant, ROUND_HALF_UP)
    if not (low <= amount <= high and 0 < deviation <= max_sigma):
        raise InvalidOperation
    amount = amount.quantize(quant, ROUND_HALF_UP)
    if amount.is_zero():
        amount = amount.copy_abs()
    return [str(amount), str(deviation)]


def parse_measurement(row, late_limit):
    raw = row["fields"]
    probe = raw["probe"].strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", probe):
        return mark(row, "isolated", "BAD_PROBE")
    try:
        measured, received = (seconds(raw[field].strip()) for field in ("observed", "received"))
    except (ValueError, OverflowError, OSError):
        return mark(row, "isolated", "BAD_TIME")
    if received < measured:
        return mark(row, "isolated", "RECEIPT_BEFORE_MEASURE")
    if normalize(raw["temp"]) in NULLS:
        return mark(row, "isolated", "NO_TEMPERATURE")
    temp_unit = normalize(raw["temp_unit"]).removeprefix("°")
    rh_unit = normalize(raw["rh_unit"])
    humidity_present = normalize(raw["rh"]) not in NULLS
    if temp_unit not in TEMP_SCALE or (humidity_present and rh_unit not in RH_SCALE):
        return mark(row, "isolated", "BAD_UNIT")
    try:
        temperature = scaled(raw["temp"], raw["temp_sigma"], *TEMP_SCALE[temp_unit], -40, 80, 10)
        humidity = scaled(raw["rh"], raw["rh_sigma"], 0, RH_SCALE[rh_unit], 1, 0, 100, 30) if humidity_present else None
    except (InvalidOperation, ArithmeticError):
        return mark(row, "isolated", "BAD_READING")
    row.update(probe=probe, measured=measured, observed_utc=utc(measured), received_utc=utc(received),
               celsius=temperature, relative_humidity=humidity, delay=received-measured,
               flags=["LATE_RECEIPT"] if received-measured > late_limit else [])
