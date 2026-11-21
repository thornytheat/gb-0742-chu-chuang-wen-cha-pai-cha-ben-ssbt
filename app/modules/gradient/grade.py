from app.modules.gradient.interval import confidence


def grade(spec, slots, rows):
    cabinets = {item.id: item for item in spec.cabinet_hours}
    evidence = {row["id"]: row for row in rows}
    result = []
    for slot in slots:
        cabinet = cabinets[slot["cabinet"]]
        gap = cabinet.upper_mm - cabinet.lower_mm
        report = {**slot, "temperature": None, "humidity": None, "state": "MISSING", "axes": [], "gap_mm": gap}
        if slot["upper"] and slot["lower"]:
            upper, lower = (evidence[slot[level]] for level in ("upper", "lower"))
            report["temperature"] = confidence(upper["celsius"], lower["celsius"], gap, cabinet.temp_limit)
            report["humidity"] = confidence(upper["relative_humidity"], lower["relative_humidity"], gap, cabinet.rh_limit)
            checks = {key: report[key]["verdict"] if report[key] else "NO_DATA" for key in ("temperature", "humidity")}
            report["axes"] = [key for key, state in checks.items() if state == "ABNORMAL"]
            if report["axes"]:
                report["state"] = "ABNORMAL"
            elif all(state == "STABLE" for state in checks.values()):
                report["state"] = "STABLE"
            else:
                report["code"] = "MISSING_RH" if report["humidity"] is None else "CI_OVERLAP"
        result.append(report)
    return result
