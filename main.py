# source .venv/bin/activate
# streamlit run main.py

#       @TODO : Avoir la position 1er 2d 3eme
#       @TODO : Permettre de lancer en mode : cache_only ou rebuild cache
#       @TODO : avoir la date du derner chargement des données
#       @TODO : Ranger le code (découper, cacher, metrics j'ai tout mis en vrac)
#       @TODO : La page doit s'afficher plus vite mettre en cache le plus possible les résultats
#       @TODO : Essayer de publier pour voir si c'est possible
#       @TODO : les indicateurs https://www.codearmo.com/blog/sharpe-sortino-and-calmar-ratios-python
#       @TODO : avoir un système de blocage si plusieurs personnes demandent en même temps car ça semble foutre la merde
#       @TODO : Ensuite un second pour le calcul des indicateur comme ça on va pouvoir isoler le code proprement 
#       @TODO : Avoir un main qui soit propre
#       @TODO : Afficher les jeunes vaults (moins de 7 jours)
#       @TODO : Afficher les vaults avec un DD de moins de 20% sur X jours (comme bybit)
#
import streamlit as st
import pandas as pd
from hyperliquid.vaults import fetch_vault_details, fetch_vaults_data
from metrics.drawdown import calculate_max_drawdown_on_accountValue, calculate_sharpe_ratio, calculate_sortino_ratio
import pandas as pd
import os
import json
from datetime import datetime

def check_date_file_exists(directory="./cache"):
    """
    Vérifie si le fichier `date.json` existe dans le répertoire spécifié.
    
    :param directory: Répertoire où le fichier est censé se trouver (par défaut /cache).
    :return: True si le fichier existe, sinon False.
    """
    # Chemin complet du fichier
    file_path = os.path.join(directory, "date.json")
    
    # Vérification de l'existence
    return os.path.exists(file_path)

def create_date_file(directory="./cache"):
    """
    Crée un fichier `date.json` dans le répertoire spécifié avec la date actuelle.
    
    :param directory: Répertoire où le fichier sera créé (par défaut /cache).
    """
    # Assurez-vous que le répertoire existe
    os.makedirs(directory, exist_ok=True)
    
    # Chemin complet du fichier
    file_path = os.path.join(directory, "date.json")
    
    # Contenu à écrire
    current_date = {"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    
    # Écriture dans le fichier
    with open(file_path, "w") as file:
        json.dump(current_date, file, indent=4)
    print(f"Fichier date.json créé dans {file_path}")


def read_date_file(directory="./cache"):
    """
    Lit et retourne la date enregistrée dans le fichier `date.json` du répertoire spécifié.
    
    :param directory: Répertoire où le fichier est situé (par défaut /cache).
    :return: La date sous forme de chaîne ou None si le fichier n'existe pas.
    """
    # Chemin complet du fichier
    file_path = os.path.join(directory, "date.json")
    
    # Vérification de l'existence du fichier
    if not os.path.exists(file_path):
        print("Fichier date.json non trouvé.")
        return None
    
    # Lecture du fichier
    with open(file_path, "r") as file:
        data = json.load(file)
        return data.get("date")

# Disposition de 3 colonnes
def slider_with_label(label, col, min_value, max_value, default_value, step, key):
    """Créer un slider avec un titre personnalisé centré."""
    col.markdown(f"<h3 style='text-align: center;'>{label}</h3>", unsafe_allow_html=True)
    if not min_value < max_value:
        col.markdown(f"<p style='text-align: center;' >Not choice available ({min_value} for all)</p>", unsafe_allow_html=True)
        return None
    
    if default_value < min_value:
        default_value = min_value

    if default_value > max_value:
        default_value = max_value

    return col.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=default_value,
        step=step,
        label_visibility="hidden",
        key=key,
    )

def calculate_average_daily_gain(rebuilded_pnl, days_since):
    """
    Calcule le % de gain moyen par jour.

    :param rebuilded_pnl: Liste des valeurs cumulées de PnL ($).
    :param days_since: Nombre de jours (int).
    :return: Gain moyen par jour en pourcentage (float).
    """
    if len(rebuilded_pnl) < 2 or days_since <= 0:
        return 0  # Pas assez de données pour calculer
    
    initial_value = rebuilded_pnl[0]
    final_value = rebuilded_pnl[-1]
    
    # Éviter les divisions par zéro
    if initial_value == 0:
        return 0  # Impossible de calculer si la valeur initiale est 0

    average_daily_gain_pct = ((final_value - initial_value) / (initial_value * days_since)) * 100
    return average_daily_gain_pct

def calculate_total_gain_percentage(rebuilded_pnl):
    """
    Calcule le pourcentage de variation totale depuis le début.

    :param rebuilded_pnl: Liste des valeurs cumulées de PnL ($).
    :return: Variation totale en pourcentage (float).
    """
    if len(rebuilded_pnl) < 2:
        return 0  # Pas assez de données pour calculer
    
    initial_value = rebuilded_pnl[0]
    final_value = rebuilded_pnl[-1]
    
    # Éviter les divisions par zéro
    if initial_value == 0:
        return 0  # Impossible de calculer si la valeur initiale est 0

    total_gain_pct = ((final_value - initial_value) / initial_value) * 100
    return total_gain_pct

limit_vault = False
# limit_vault = True


st.set_page_config(layout="wide")  # Page en full largeur

if not check_date_file_exists():
    create_date_file()

data_date = read_date_file()

# Étape 1 : Récupération des données des vaults
vaults = fetch_vaults_data()

# Limiter à 50 premières vaults
if limit_vault:
    vaults = vaults[:50]

# Étape 3 : Collecter les historiques PNL pour chaque vault et calculer les indicateurs

st.markdown(f"<h3 style='text-align: center;'>Data downloaded {data_date} </h3>", unsafe_allow_html=True)



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

    nb_followers = 0
    if details and "followers" in details :
        for idx, value in enumerate(details['followers']):
            if float(value['vaultEquity']) >= 0.01:
                nb_followers = nb_followers + 1


    if details and "portfolio" in details :


        if details["portfolio"][3][0] == "allTime":
            data_source_pnlHistory          = details["portfolio"][3][1].get("pnlHistory", [])
            data_source_accountValueHistory = details["portfolio"][3][1].get("accountValueHistory", [])
            rebuilded_pnl = []

            balance = start_balance_amount = 1000000
            nb_rekt = 0
            last_rekt_idx = -10


            # recalcul la balance sans tenir compte des mouvement des depositors
            for idx, value in enumerate(data_source_pnlHistory):
                if idx == 0:
                    continue

                # capital à l'instant T
                final_capital           = float(data_source_accountValueHistory[idx][1])
                # PNL cumulé à l'instant T
                final_cumulated_pnl     = float(data_source_pnlHistory[idx][1])
                # PNL cumulé à l'instant T -1
                previous_cumulated_pnl  = float(data_source_pnlHistory[idx-1][1]) if idx > 0 else 0
                # PNL NON cumulé à l'instant T
                final_pnl               = final_cumulated_pnl - previous_cumulated_pnl
                # capital avant le gain/perte
                initial_capital         = final_capital - final_pnl
                
                if initial_capital <= 0:
                    if last_rekt_idx+1 != idx:
                        rebuilded_pnl = []
                        balance = start_balance_amount
                        nb_rekt = nb_rekt + 1
                    last_rekt_idx = idx
                    continue
                # ratio de gain / perte
                ratio = final_capital / initial_capital

                # verification de la cohérence des timestamp
                if data_source_pnlHistory[idx][0] != data_source_accountValueHistory[idx][0]:
                    print('Just to check, normaly, not arriving')
                    exit()

                # modification de la balance fictive
                balance = balance * ratio

                rebuilded_pnl.append(balance)



            metrics =   {
                            "Max DD %": calculate_max_drawdown_on_accountValue(rebuilded_pnl),
                            "Rekt": nb_rekt,
                            "Act. Followers": nb_followers,
                            "Sharpe Ratio": calculate_sharpe_ratio(rebuilded_pnl),
                            "Sortino Ratio": calculate_sortino_ratio(rebuilded_pnl),
                            "Av. Daily Gain %": calculate_average_daily_gain(rebuilded_pnl, vault['Days Since']),
                            "Gain %": calculate_total_gain_percentage(rebuilded_pnl),
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


# Filtre sur 'Name' (dernier filtre, en texte libre)
st.markdown("<h3 style='text-align: center;'>Filter by Name</h3>", unsafe_allow_html=True)
name_filter = st.text_input(
    "Name Filter", 
    "", 
    placeholder="Enter names separated by ',' to filter (e.g., toto,tata)...", 
    key="name_filter"
)

# Appliquer le filtre
if name_filter.strip():  # Vérifier que le filtre n'est pas vide
    name_list = [name.strip() for name in name_filter.split(",")]  # Liste des noms à chercher
    pattern = "|".join(name_list)  # Créer un pattern regex avec "ou" logique
    filtered_df = filtered_df[
        filtered_df["Name"].str.contains(pattern, case=False, na=False, regex=True)
    ]

# Organisation des sliders en lignes de 3
sliders = [
    {"label": "Min Sharpe Ratio",           "column": "Sharpe Ratio",       "max": False, "default": 0.4,   "step": 0.1},
    {"label": "Min Sortino Ratio",          "column": "Sortino Ratio",      "max": False, "default": 0.5,   "step": 0.1},
    {"label": "Max Rekt accepted",          "column": "Rekt",               "max": True, "default": 0,   "step": 1},
    {"label": "Max DD % accepted",          "column": "Max DD %",           "max": True, "default": 15,  "step": 1},
    {"label": "Min Days Since accepted",    "column": "Days Since",         "max": False, "default": 100, "step": 1},
    {"label": "Min TVL accepted",           "column": "Total Value Locked", "max": False, "default": 4000, "step": 1},
    {"label": "Min APR accepted",           "column": "APR %",              "max": False, "default": 0,  "step": 1},
    {"label": "Min Followers",              "column": "Act. Followers",     "max": False, "default": 0,  "step": 1},
]

for i in range(0, len(sliders), 3):
    cols = st.columns(3)
    for slider, col in zip(sliders[i:i+3], cols):
        column = slider["column"]
        value = slider_with_label(
            slider["label"], col,
            min_value=float(filtered_df[column].min()),
            max_value=float(filtered_df[column].max()),
            default_value=float(slider["default"]),
            step=float(slider["step"]),
            key=f"slider_{column}"
        )
        if not value == None:
            if slider["max"]:
                filtered_df = filtered_df[filtered_df[column] <= value]
            else:
                filtered_df = filtered_df[filtered_df[column] >= value]

# Afficher le tableau
st.title(f"Vaults filtered ({len(filtered_df)}) ")

# Ajouter une colonne de liens cliquables
filtered_df["Link"] = filtered_df["Vault"].apply(
    lambda vault: f'https://app.hyperliquid.xyz/vaults/{vault}'
)

# Réinitialiser l'index pour obtenir un classement continu
filtered_df = filtered_df.reset_index(drop=True)


st.dataframe(
    filtered_df, 
    use_container_width=True, 
    height=(len(filtered_df) * 35) + 50,  # Ajuste la hauteur selon le nombre de lignes
    column_config={
        "Link": st.column_config.LinkColumn(
            "Vault Link",
            display_text="Vault Link",
        )
    }
)

