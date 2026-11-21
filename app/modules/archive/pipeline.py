from collections import Counter

from app.modules.assignment.windows import DeploymentIndex, assign
from app.modules.audit.reconcile import reconcile
from app.modules.episodes.segment import segment
from app.modules.gradient.grade import grade
from app.modules.intake.readings import deduplicate, read
from app.modules.pairing.schedule import schedule


def evaluate(package):
    spec = package.spec
    rows, intake = read(package)
    deduplicate(rows)
    index = DeploymentIndex(spec)
    assign(spec, rows, index)
    pairs, unused = schedule(spec, rows, index)
    grades = grade(spec, pairs, rows)
    episodes = segment(grades, spec.sustained_hours)
    audit = reconcile(spec, rows, intake, grades, episodes)
    return {"intake": intake, "rows": rows, "deployments": index.windows, "deployment_conflicts": index.conflicts,
            "pairs": pairs, "unused": unused, "grades": grades, "episodes": episodes, "audit": audit,
            "isolation": dict(sorted(Counter(row["code"] for row in rows if row["disposition"] == "isolated").items()))}
