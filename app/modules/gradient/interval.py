from decimal import Decimal, ROUND_HALF_UP, localcontext


def display(value):
    return str(value.quantize(Decimal("0.001"), ROUND_HALF_UP))


def confidence(upper, lower, height_mm, limit):
    if upper is None or lower is None:
        return None
    up, up_sigma = map(Decimal, upper)
    down, down_sigma = map(Decimal, lower)
    with localcontext() as ctx:
        ctx.prec = 38
        scale = Decimal(1000) / height_mm
        center = (up - down) * scale
        half_width = Decimal("1.96") * (up_sigma**2 + down_sigma**2).sqrt() * scale
        low, high = center - half_width, center + half_width
        if low > limit or high < -limit:
            verdict = "ABNORMAL"
        elif -limit <= low and high <= limit:
            verdict = "STABLE"
        else:
            verdict = "UNCERTAIN"
        return {"value": display(center), "low": display(low), "high": display(high),
                "limit": str(limit), "verdict": verdict}
