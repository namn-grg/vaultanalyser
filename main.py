# source .venv/bin/activate
# streamlit run main.py

#
#       @TODO : les indicateurs https://www.codearmo.com/blog/sharpe-sortino-and-calmar-ratios-python
#       @TODO : avoir un système de blocage si plusieurs personnes demandent en même temps car ça semble foutre la merde
#       @TODO : en fait il faut faire un tour de piste que pour le DL
#       @TODO : Ensuite un second pour le calcul des indicateur comme ça on va pouvoir isoler le code proprement 
#       @TODO : Avoir un main qui soit propre
#       @TODO : Afficher le nb jours depuis AJD plutot que date création
#       @TODO : pouvoir avoir des filtres sur le tableau pour dire que je veux les DD > à X, nb jours > à Y
#
#
import streamlit as st
import pandas as pd
import json
import numpy as np
from datetime import datetime
from hyperliquid.vaults import fetch_vault_details, fetch_vaults_data
from metrics.drawdown import calculate_max_drawdown_on_accountValue

st.set_page_config(layout="wide")  # Page en full largeur


# Étape 1 : Récupération des données des vaults
vaults = fetch_vaults_data()

# Limiter à 50 premières vaults
vaults = vaults[:500]

# Étape 3 : Collecter les historiques PNL pour chaque vault et calculer les indicateurs




progress_bar = st.progress(0)  # Barre de progression (de 0 à 1)
status_text = st.empty()  # Texte affichant l'état
status_text.text(f"Downloading vaults details...")
total_steps=len(vaults)
indicators = []
progress_i=1
for vault in vaults:
    # print(json.dumps(vault, indent=4))
    details = fetch_vault_details(vault["Leader"], vault["Vault"])

    progress_bar.progress(progress_i / total_steps)
    progress_i=progress_i+1

    if details and "portfolio" in details and len(details["portfolio"]) > 3:
        pnl_history = details["portfolio"][3][1].get("accountValueHistory", [])
        pnl_values = np.array([float(pnl[1]) for pnl in pnl_history])
        metrics =   {
                        "Max DD": calculate_max_drawdown_on_accountValue(pnl_values)
                    }
        indicator_row = {
            "Name": vault["Name"], 
            **metrics  # Unpacks the metrics dictionary
        }
        indicators.append(indicator_row)
    
progress_bar.empty()
status_text.empty()

st.toast("Vault details OK !", icon="✅")








# Étape 4 : Fusionner les indicateurs avec le tableau principal
indicators_df = pd.DataFrame(indicators)
vaults_df = pd.DataFrame(vaults)
del vaults_df['Leader']
final_df = vaults_df.merge(indicators_df, on="Name", how="left")

# Afficher le tableau
st.title(f"Liste des Vaults Actives ({len(final_df)}) Vaults")
st.write(final_df)