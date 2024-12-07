# source .venv/bin/activate
# streamlit run main.py

#
#       @TODO : Afficher le nombre de followers et pouvoir trier
#       @TODO : en fait, ce servire de tedy57123 car on a une rupture aussi
#               https://app.hyperliquid.xyz/vaults/0x7bde2b9240a2ee352108c6823a9fa20f225b83a0
#               en fait faut prendre le gain et le capital de fin du coup on a le capital de début
#               donc on connait le %
#               et il faut appliquer ce % au capital actuel (1000 le jour J) puis la suite
#               ce serait probablement un bon algo
#               le soucis c'est quans il y a des nouveau entrant, par exemple cette vault
#               https://app.hyperliquid.xyz/vaults/0x702255357a886ee309c4b82bd61ae9783a4e6d5d
#               a mon avis il faut jouer avec PnlHistory et Acount history
#               accountValueHistory : 39 [1733603883437, "182075.68717"]
#               pnlHistory : 39 : [1733603883437, "49039.423212"] 
#               le capital était de (182075.68717 - 49039.423212)
#               le capital après action est de 182075.68717
#               le gain est de 182075,68717 * 100 / (182075,68717 - 49039,423212) - 100 =  36%
#               j'ai peur que ce ne soit pas possible en fait... j'arrive pas à savoir
#       @TODO : La page doit s'afficher plus vite mettre en cache le plus possible les résultats
#       @TODO : Je pense que le système de cache de vault detail n'est pas optimum il est très lent
#       @TODO : en fait il faut faire un tour de piste que pour le DL
#               le code avec la progress barre de DLdu détail devrait être en 2 fois, une fois les données, une fois le calcul
#               et il devrait aussi être plus isolé
#       @TODO : Essayer de publier pour voir si c'est possible
#       @TODO : Mettre un lien vers les vaults
#       @TODO : les indicateurs https://www.codearmo.com/blog/sharpe-sortino-and-calmar-ratios-python
#       @TODO : avoir un système de blocage si plusieurs personnes demandent en même temps car ça semble foutre la merde
#       @TODO : Ensuite un second pour le calcul des indicateur comme ça on va pouvoir isoler le code proprement 
#       @TODO : Avoir un main qui soit propre
#       @TODO : Afficher le nb jours depuis AJD plutot que date création
#       @TODO : pouvoir avoir des filtres sur le tableau pour dire que je veux les DD > à X, nb jours > à Y
#       @TODO : Afficher les jeunes vaults (moins de 7 jours)
#       @TODO : Afficher les vaults avec un DD de moins de 20%
#       @TODO : 
#
import streamlit as st
import pandas as pd
import json
import numpy as np
from datetime import datetime
from hyperliquid.vaults import fetch_vault_details, fetch_vaults_data
from metrics.drawdown import calculate_max_drawdown_on_accountValue

limit_vault = False
# limit_vault = True


st.set_page_config(layout="wide")  # Page en full largeur


# Étape 1 : Récupération des données des vaults
vaults = fetch_vaults_data()

# Limiter à 50 premières vaults
if limit_vault:
    vaults = vaults[:50]

# Étape 3 : Collecter les historiques PNL pour chaque vault et calculer les indicateurs




progress_bar = st.progress(0)  # Barre de progression (de 0 à 1)
status_text = st.empty()  # Texte affichant l'état
status_text.text(f"Downloading vaults details...")
total_steps=len(vaults)
indicators = []
progress_i=1
for vault in vaults:

    vault_to_log = "" #"0x9c823dab050a2b6f0b549d89b8f0b909f6936a92"

    # print(json.dumps(vault, indent=4))
    details = fetch_vault_details(vault["Leader"], vault["Vault"])

    if vault['Vault'] == vault_to_log:
        print('') 
        print('----- ', vault["Vault"])

    progress_bar.progress(progress_i / total_steps)
    progress_i=progress_i+1
    status_text.text(f"Downloading vaults details ({progress_i}/{total_steps})...")

    if details and "portfolio" in details :


        if details["portfolio"][3][0] == "allTime":
            data_source_pnlHistory          = details["portfolio"][3][1].get("pnlHistory", [])
            data_source_accountValueHistory = details["portfolio"][3][1].get("accountValueHistory", [])
            rebuilded_pnl = []

            balance = 1000000

            # recalcul la balance sans tenir compte des mouvement des depositors
            for idx, value in enumerate(data_source_pnlHistory):
                
                previous_pnlHistory             = float(data_source_pnlHistory[idx-1][1]) if idx > 0 else 0
                actual_pnlHistory               = float(data_source_pnlHistory[idx  ][1])
                profit                          = actual_pnlHistory - previous_pnlHistory

                after_profit = float(data_source_accountValueHistory[idx][1])
                before_profit = after_profit - profit

                if data_source_pnlHistory[idx][1] == 0 and data_source_accountValueHistory[idx][1] == 0:
                    continue

                if data_source_pnlHistory[idx][0] != data_source_accountValueHistory[idx][0]:
                    print('Just to check, normaly, not arriving')
                    exit()

                if before_profit > 0 :
                    if vault['Vault'] == vault_to_log:
                        print(idx, "after_profit " , after_profit, "/ before_profit ", before_profit)
                    ratio = after_profit / before_profit
                    # print("balance ", balance)
                    balance = balance * ratio
                    if vault['Vault'] == vault_to_log:
                        print(idx, "profit " , profit, "/ balance ", balance, ' / vault ', vault["Vault"])
                    rebuilded_pnl.append(balance)



            metrics =   {
                            "Max DD %": calculate_max_drawdown_on_accountValue(rebuilded_pnl)
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


# les filtres
st.subheader(f"Vaults available ({len(final_df)})")
filtered_df = final_df

# Utiliser Markdown pour ajuster la taille du texte du label
st.markdown("<h3 style='text-align: center;'>Max DD % accepted</h3>", unsafe_allow_html=True)
max_dd_value = st.slider(
    "Max DD % accepted",
    min_value=int(filtered_df["Max DD %"].min()),
    max_value=int(filtered_df["Max DD %"].max()),
    value=16,
    step=1,
    label_visibility="hidden",
    
)
filtered_df = filtered_df[final_df["Max DD %"]                <= max_dd_value]

st.markdown("<h3 style='text-align: center;'>Min Days Since accepted</h3>", unsafe_allow_html=True)
min_dayssince_value = st.slider(
    "Min Days Since accepted",
    min_value=int(filtered_df["Days Since"].min()),
    max_value=int(filtered_df["Days Since"].max()),
    step=1,
    label_visibility="hidden",
    value=124
)
filtered_df = filtered_df[final_df["Days Since"]            >= min_dayssince_value]

st.markdown("<h3 style='text-align: center;'>Min TVL accepted</h3>", unsafe_allow_html=True)
min_tvl_value = st.slider(
    "Min TVL accepted",
    min_value=int(filtered_df["Total Value Locked"].min()),
    max_value=int(filtered_df["Total Value Locked"].max()),
    step=1,
    label_visibility="hidden",
    value=6000
)
filtered_df = filtered_df[final_df["Total Value Locked"]    >= min_tvl_value]

st.markdown("<h3 style='text-align: center;'>Min APR accepted</h3>", unsafe_allow_html=True)
min_apr_value = st.slider(
    "Min APT accepted",
    min_value=int(filtered_df["APR %"].min()),
    max_value=int(filtered_df["APR %"].max()),
    step=1,
    label_visibility="hidden",
    value=200
)
filtered_df = filtered_df[final_df["APR %"]    >= min_apr_value]

# Afficher le tableau
st.title(f"Vaults filtered ({len(filtered_df)}) ")
st.dataframe(filtered_df, use_container_width=True, height=(len(filtered_df) * 35) + 50  # Ajuste la hauteur selon le nombre de lignes
)