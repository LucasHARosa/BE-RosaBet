def calculate_return(value: float, quotations: list[float]) -> tuple[float, float]:
    total = 1.0
    for q in quotations:
        total *= q
    return round(total, 4), round(value * total, 2)
