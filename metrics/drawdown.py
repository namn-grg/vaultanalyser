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