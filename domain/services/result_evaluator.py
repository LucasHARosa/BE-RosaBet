import random


def get_main_market_odds(markets):
    for pid in [1, 219, 186]:
        for m in markets:
            if m.market_id == pid:
                return m.market_id, m.odds
    return markets[0].market_id, markets[0].odds


def generate_outcome(odds: list) -> str:
    probs = {o.option_id: 1 / float(o.value) for o in odds}
    total = sum(probs.values())
    norm = {k: v / total for k, v in probs.items()}
    return random.choices(list(norm.keys()), weights=list(norm.values()))[0]


def evaluate_outcome(market_id: int, option_id: str, specifier: dict | None, home: int, away: int) -> bool:
    if market_id == 1:
        if home > away: return option_id == "1"
        if home == away: return option_id == "X"
        return option_id == "2"

    if market_id in (186, 219):
        return (option_id == "1") == (home > away)

    if market_id == 3:
        scored = home > 0 and away > 0
        return (option_id == "yes") == scored

    if market_id == 5:
        threshold = float((specifier or {}).get("total", "2.5"))
        total = home + away
        if option_id == "over": return total > threshold
        if option_id == "under": return total < threshold

    if market_id == 10:
        if option_id == "1X": return home >= away
        if option_id == "X2": return away >= home
        if option_id == "12": return home != away

    if market_id in (29, 45):
        if home > away: return option_id == "1"
        if home == away: return option_id == "X"
        return option_id == "2"

    return False
