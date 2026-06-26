import math
import random


def fluctuate_odd(current: float, is_live: bool, minute: int = 0) -> float:
    """
    Varia uma odd com base em volatilidade proporcional à odd atual e ao momento da partida.
    Odds mais altas oscilam mais. Próximo do fim, a volatilidade aumenta.
    """
    base_volatility = 0.008 if is_live else 0.002

    if is_live and minute > 75:
        base_volatility *= 1.5

    volatility = base_volatility * math.log(current + 1)
    delta = random.gauss(0, volatility)
    delta = max(-0.05, min(0.05, delta))

    new_value = round(current + delta, 2)
    return max(1.01, min(100.0, new_value))


def generate_correlated_odds(odds: list[dict], is_live: bool, minute: int = 0) -> list[dict]:
    """
    Varia um conjunto de odds de um mercado mantendo margem da casa ~7%.
    Se uma odd cai, as demais sobem proporcionalmente para manter o equilíbrio.
    Cada dict deve ter: {"odd_id": str, "value": float}
    Retorna lista com {"odd_id": str, "value": float, "prev_value": float}
    """
    updated = []
    for o in odds:
        new_val = fluctuate_odd(float(o["value"]), is_live, minute)
        updated.append({**o, "prev_value": float(o["value"]), "value": new_val})

    # normaliza para manter margem da casa ~7%
    # soma das probs implícitas deve ser ~1.07 (não 1.0)
    target_overround = 1.07
    total_prob = sum(1.0 / o["value"] for o in updated)
    if total_prob > 0:
        scale = target_overround / total_prob
        # se scale está muito longe de 1 (odds colapsaram), aplica só 20% da correção
        # para evitar que a normalização empurre valores abaixo do mínimo
        if scale < 0.5 or scale > 2.0:
            scale = 1.0 + (scale - 1.0) * 0.2
        for o in updated:
            o["value"] = round(o["value"] * scale, 2)
            o["value"] = max(1.01, o["value"])

    return updated
