from collections import defaultdict
from itertools import combinations

from app.reasons import mark
from app.timebase import seconds, utc


class DeploymentIndex:
    def __init__(self, spec):
        self.windows = []
        self.by_probe = defaultdict(list)
        self.blocked = defaultdict(list)
        self.conflicts = []
        for ordinal, source in enumerate(spec.deployments, 1):
            window = {**source.model_dump(), "id": f"D{ordinal:02d}",
                      "begin": seconds(source.start), "stop": seconds(source.end)}
            self.windows.append(window)
            self.by_probe[source.probe].append(window)
        for first, second in combinations(self.windows, 2):
            start, end = max(first["begin"], second["begin"]), min(first["stop"], second["stop"])
            by_probe = first["probe"] == second["probe"]
            by_position = (first["cabinet"], first["level"]) == (second["cabinet"], second["level"])
            if start < end and (by_probe or by_position):
                for window in (first, second):
                    self.blocked[window["id"]].append((start, end))
                self.conflicts.append({"deployments": [first["id"], second["id"]], "start": utc(start), "end": utc(end),
                                       "probe_conflict": by_probe, "position_conflict": by_position})

    def resolve(self, probe, moment):
        options = [window for window in self.by_probe.get(probe, []) if window["begin"] <= moment < window["stop"]]
        if not options:
            return None, "NO_DEPLOYMENT"
        if len(options) > 1 or not self.available(options[0], moment):
            return None, "DEPLOYMENT_CONFLICT"
        return options[0], None

    def available(self, window, moment):
        return window["begin"] <= moment < window["stop"] and all(
            not start <= moment < end for start, end in self.blocked.get(window["id"], []))

    def continuous(self, window, a, b):
        start, end = sorted((a, b))
        return window["begin"] <= start <= end < window["stop"] and all(
            end < bad_start or bad_end <= start for bad_start, bad_end in self.blocked.get(window["id"], []))


def assign(spec, rows, index):
    start, end = seconds(spec.start), seconds(spec.end)
    for row in rows:
        if row["disposition"] != "accepted":
            continue
        if not start <= row["measured"] < end:
            mark(row, "isolated", "OFF_SHIFT")
            continue
        window, reason = index.resolve(row["probe"], row["measured"])
        if reason:
            mark(row, "isolated", reason)
            continue
        row["deployment"] = window
