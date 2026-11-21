from itertools import groupby


def segment(grades, sustained_hours):
    abnormal = sorted((slot for slot in grades if slot["state"] == "ABNORMAL"), key=lambda item: (item["cabinet"], item["hour"]))
    episodes = []
    for cabinet, items in groupby(abnormal, key=lambda item: item["cabinet"]):
        groups = groupby(enumerate(items), key=lambda item: item[1]["hour"] - item[0] * 3600)
        for index, (_, group) in enumerate(groups, 1):
            members = [slot for _, slot in group]
            duration = len(members)
            episodes.append({"id": f"{cabinet}-A{index:02d}", "cabinet": cabinet, "start": members[0]["start"],
                             "end": members[-1]["end"], "hours": duration,
                             "kind": "SUSTAINED" if duration >= sustained_hours else "TRANSIENT",
                             "axes": sorted({axis for slot in members for axis in slot["axes"]}),
                             "evidence": [{"start": slot["start"], "upper": slot["upper"], "lower": slot["lower"]}
                                          for slot in members]})
    return episodes
