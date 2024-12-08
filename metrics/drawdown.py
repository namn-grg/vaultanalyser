def calculate_max_drawdown_on_accountValue(cumulative_pnl):
    """
    Calcule le maximum drawdown à partir d'une liste de PnL cumulée par jour.

    :param cumulative_pnl: Liste des valeurs cumulées de PnL par jour
    :return: Le maximum drawdown en valeur absolue et en pourcentage
    """
    # Initialisation des variables
    max_value = float('-inf')  # La valeur maximale atteinte à un moment donné
    max_drawdown = 0  # La plus grande baisse enregistrée

    for pnl in cumulative_pnl:
        # Mise à jour du maximum atteint
        max_value = max(max_value, pnl)
        # Calcul du drawdown courant
        drawdown = max_value - pnl
        # Mise à jour si drawdown actuel est le plus élevé
        max_drawdown = max(max_drawdown, drawdown)

    # Calcul du drawdown en pourcentage (par rapport au pic maximum)
    max_drawdown_pct = (max_drawdown / max_value * 100) if max_value != 0 else 0

    return int(max_drawdown_pct)



def calculate_sortino_ratio(daily_pnl, risk_free_rate=0.0):
    """
    Calcule le Sortino Ratio à partir des rendements journaliers.
    :param daily_pnl: Liste des PnL journaliers.
    :param risk_free_rate: Taux de rendement sans risque (par défaut : 0%).
    :return: Sortino Ratio.
    """
    returns = [pnl / daily_pnl[i - 1] - 1 for i, pnl in enumerate(daily_pnl[1:], 1) if daily_pnl[i - 1] != 0]
    if len(returns) == 0:
        return 0
    avg_return = sum(returns) / len(returns)
    downside_deviation = (
        sum((min(r - risk_free_rate, 0) ** 2 for r in returns)) / len(returns)
    ) ** 0.5
    if downside_deviation == 0:
        return 0
    return avg_return / downside_deviation

def calculate_sharpe_ratio(daily_pnl, risk_free_rate=0.0):
    """
    Calcule le Sharpe Ratio à partir des rendements journaliers.
    :param daily_pnl: Liste des PnL journaliers.
    :param risk_free_rate: Taux de rendement sans risque (par défaut : 0%).
    :return: Sharpe Ratio.
    """
    returns = [pnl / daily_pnl[i - 1] - 1 for i, pnl in enumerate(daily_pnl[1:], 1) if daily_pnl[i - 1] != 0]
    if len(returns) == 0:
        return 0
    avg_return = sum(returns) / len(returns)
    std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
    if std_dev == 0:
        return 0
    return avg_return / std_dev