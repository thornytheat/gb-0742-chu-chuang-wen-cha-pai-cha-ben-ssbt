from array import array
from bisect import bisect_left, bisect_right


def eligible(upper, lower, index):
    a, b = upper["measured"], lower["measured"]
    return index.continuous(upper["deployment"], a, b) and index.continuous(lower["deployment"], a, b)


def best_edges(uppers, lowers, lower_times, tolerance, index):
    edges = {}
    for rank, upper in enumerate(uppers):
        moment = upper["measured"]
        left = bisect_left(lower_times, moment - tolerance)
        right = bisect_right(lower_times, moment + tolerance)
        for j in range(left, right):
            edge = (abs(lower_times[j] - moment), rank)
            if eligible(upper, lowers[j], index) and (j not in edges or edge < edges[j]):
                edges[j] = edge
    return edges


def optimal_matching(upper_slots, lowers, tolerance, index):
    """Maximize distinct matched hours, then minimize their total time drift."""
    # Valid edges stay in a continuous deployment span. Within a span,
    # uncrossing time-ordered pairs preserves the tolerance and cannot add drift.
    size = len(lowers)
    lower_times = [row["measured"] for row in lowers]
    choices = [array("H", [0]) * size for _ in upper_slots]
    scores = [(0, 0)] * (size + 1)
    with_candidates = set()
    for i in range(len(upper_slots) - 1, -1, -1):
        edges = best_edges(upper_slots[i], lowers, lower_times, tolerance, index)
        if edges:
            with_candidates.add(i)
        next_scores = scores
        scores = [(0, 0)] * (size + 1)
        for j in range(size - 1, -1, -1):
            best = max((next_scores[j], 1), (scores[j + 1], 2))
            if j in edges:
                drift, rank = edges[j]
                count, negative_drift = next_scores[j + 1]
                best = max(best, ((count + 1, negative_drift - drift), rank + 3))
            scores[j], choices[i][j] = best
    matched = {}
    i = j = 0
    while i < len(upper_slots) and j < size:
        action = choices[i][j]
        if action >= 3:
            matched[i] = (action - 3, j)
        i += action != 2
        j += action != 1
    return matched, with_candidates
