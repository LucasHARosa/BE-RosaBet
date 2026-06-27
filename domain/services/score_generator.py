import random


def generate_score(outcome: str, sport_type: str) -> tuple[int, int]:
    if sport_type == "Soccer":
        if outcome == "1":
            return random.choice([(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (3, 2), (4, 1)])
        if outcome == "X":
            return random.choice([(0, 0), (0, 0), (1, 1), (1, 1), (2, 2)])
        return random.choice([(0, 1), (0, 2), (1, 2), (0, 3), (1, 3), (2, 3)])

    if sport_type == "Basketball":
        base = random.randint(90, 118)
        diff = random.randint(3, 22)
        if outcome == "1":
            return (base + diff, base)
        return (base, base + diff)

    if sport_type == "Tennis":
        if outcome == "1":
            return random.choice([(2, 0), (2, 1)])
        return random.choice([(0, 2), (1, 2)])

    if outcome == "1":
        return (1, 0)
    return (0, 1)
