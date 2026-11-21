import csv
import io
from collections import defaultdict

from app.errors import FieldError
from app.modules.intake.values import parse_measurement
from app.reasons import mark

HEADER = ("probe", "observed", "received", "temp", "temp_unit", "temp_sigma", "rh", "rh_unit", "rh_sigma", "memo")
NAMES = dict(zip(("探头", "测量", "收报", "温度", "温标", "温度误差", "湿度", "湿度单位", "湿度误差", "备注"), HEADER))


def decode(blob):
    for codec in ("utf-8-sig", "gb18030"):
        try:
            text = blob.decode(codec)
        except UnicodeDecodeError:
            continue
        if "\x00" in text:
            break
        return text, "utf-8" if codec == "utf-8-sig" and not blob.startswith(b"\xef\xbb\xbf") else codec
    raise FieldError("BAD_ENCODING", "点位图档编码无效")


def read(package):
    content, encoding = decode(package.blob)
    reader = csv.reader(io.StringIO(content, newline=""), strict=True)
    rows, segments, data_count, columns = [], 0, 0, None
    try:
        while True:
            first = reader.line_num + 1
            fields = next(reader, None)
            if fields is None:
                break
            cells = [value.strip().lower().lstrip("\ufeff") for value in fields]
            keys = [NAMES.get(value, value) for value in cells]
            is_header = len(keys) == len(HEADER) and set(keys) == set(HEADER)
            row = {"id": f"{package.spec.csv}:{first}", "line": first, "end_line": reader.line_num,
                   "raw": fields, "disposition": "accepted", "code": None}
            if is_header:
                columns = keys
                segments += 1
                if segments == 1:
                    continue
                mark(row, "header", "HEADER_REPEAT")
            elif not any(cells):
                mark(row, "blank", "EMPTY_LINE")
            elif columns is None:
                raise FieldError("BAD_HEADER", "首段栏头不完整")
            else:
                data_count += 1
                if len(fields) != len(columns):
                    mark(row, "isolated", "WRONG_WIDTH")
                else:
                    row["fields"] = dict(zip(columns, fields))
                    parse_measurement(row, package.spec.late_seconds)
            rows.append(row)
    except csv.Error as exc:
        raise FieldError("BROKEN_CSV", f"图档第 {reader.line_num} 行损坏") from exc
    if data_count != package.spec.records:
        raise FieldError("TRUNCATED_INPUT", f"声明 {package.spec.records} 条，实收 {data_count} 条")
    return rows, {"encoding": encoding, "segments": segments, "declared": data_count, "physical": reader.line_num}


def deduplicate(rows):
    grouped = defaultdict(list)
    for row in rows:
        if row["disposition"] == "accepted":
            grouped[row["probe"], row["measured"]].append(row)
    for duplicates in grouped.values():
        if len(duplicates) == 1:
            continue
        measurements = {(tuple(row["celsius"]), tuple(row["relative_humidity"] or [])) for row in duplicates}
        if len(measurements) > 1:
            for row in duplicates:
                mark(row, "isolated", "READING_CONFLICT")
        else:
            earliest = min(duplicates, key=lambda row: (row["delay"], row["line"]))
            for row in duplicates:
                if row is not earliest:
                    mark(row, "duplicate", "DUPLICATE_READING")
