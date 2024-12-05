# source .venv/bin/activate
# streamlit run main.py

import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime, timedelta

st.set_page_config(layout="wide")  # Page en full largeur

URL = "https://stats-data.hyperliquid.xyz/Mainnet/vaults"
CACHE_FILE = "vaults_cache.json"

def get_data():
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            last_update = datetime.fromisoformat(cache["last_update"])
            if datetime.now() - last_update < timedelta(days=1):
                return cache["data"]
    except (FileNotFoundError, KeyError, ValueError):
        pass
    response = requests.get(URL)
    data = response.json()
    with open(CACHE_FILE, "w") as f:
        json.dump({"last_update": datetime.now().isoformat(), "data": data}, f)
    return data

data = get_data()

# Préparer les données
vaults = [
    {
        "APR %": int(vault["apr"]*100),
        "Name": vault["summary"]["name"],
        "Address": vault["summary"]["vaultAddress"],
        "Total Value Locked": float(vault["summary"]["tvl"]),
        "Created Date": datetime.fromtimestamp(vault["summary"]["createTimeMillis"] / 1000).strftime("%d/%m/%Y"),
        # "is_closed": vault["summary"]["isClosed"],
        # "all_time": list(map(float, vault["pnls"][3][1])),  # "allTime"
    }
    for vault in data
    if not vault["summary"]["isClosed"]
]

# Extraire uniquement les valeurs nécessaires pour les graphiques
# graph_data = [{"name": vault["name"], "all_time": vault["all_time"]} for vault in vaults]

# Créer un DataFrame pour afficher les données de base
df = pd.DataFrame(vaults)


# Ajouter un graphique pour chaque "vault" avec le code JavaScript
st.title(f"Liste des Vaults Actives {len(df)} Vaults")

# Afficher les données dans un tableau triable
st.write(df)


