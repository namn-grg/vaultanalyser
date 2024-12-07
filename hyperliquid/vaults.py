import requests
import os
import json
import re
from datetime import datetime, timedelta
import streamlit as st


# URL pour les vaults
VAULTS_URL = "https://stats-data.hyperliquid.xyz/Mainnet/vaults"
INFO_URL = "https://api-ui.hyperliquid.xyz/info"

CACHE_DIR="./cache/"

CACHE_FILE = CACHE_DIR + "vaults_cache.json"
DETAILS_CACHE_FILE = CACHE_DIR + "/vault_detail/#KEY#/vault_details_cache.json"


CACHE_DAYS_VALIDITY=7

def fetch_vaults_data(): 
    """Récupère les données des vaults (avec cache)."""

    # Initialisation de la barre de progression et du compteur
    progress_bar = st.progress(0)  # Barre de progression (de 0 à 1)
    status_text = st.empty()  # Texte affichant l'état
    status_text.text(f"Downloading vault list...")

    cache_used = False

    # Cache already exist ?
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            cache_used = True
            vaults = cache["data"]
    except (FileNotFoundError, KeyError, ValueError):
        pass

    if not cache_used: # Cache n'existe pas
        response = requests.get(VAULTS_URL)
        data = response.json()
            
        # Étape 2 : Préparer les données des vaults
        vaults = [
            {
                "Name": vault["summary"]["name"],
                "APR %": int(vault["apr"] * 100),
                "Vault": vault["summary"]["vaultAddress"],
                "Leader": vault["summary"]["leader"],
                "Total Value Locked": float(vault["summary"]["tvl"]),
                "Days Since": (datetime.now() - datetime.fromtimestamp(vault["summary"]["createTimeMillis"] / 1000)).days,
            }
            for vault in data if not vault["summary"]["isClosed"]
        ]

        with open(CACHE_FILE, "w") as f:
            json.dump({"last_update": datetime.now().isoformat(), "data": vaults}, f)

    progress_bar.progress(100)  # Barre de progression (de 0 à 1)
    if cache_used:
        status_text.text(f"Vault List cache used")
    else:
        status_text.text(f"Fresh vault List downloaded")

    progress_bar.empty()
    status_text.empty()

    if not cache_used:
        st.toast("Vault list OK !", icon="✅")


    return vaults

def fetch_vault_details(leader, vault_address):
    """Récupère les détails d'une vault avec un système de cache."""
    
    cache_key = re.sub(r"[^a-zA-Z0-9_]", "", leader + "_" + vault_address)
    local_DETAILS_CACHE_FILE = DETAILS_CACHE_FILE.replace('#KEY#', cache_key)
    
    # Extraire le chemin des répertoires sans le fichier
    directory_path = os.path.dirname(local_DETAILS_CACHE_FILE)

    # Créer les répertoires si besoin
    os.makedirs(directory_path, exist_ok=True)

    try:
        with open(local_DETAILS_CACHE_FILE, "r") as f:
            # print("Vault DETAIL : cache used ", cache_key)
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print('Vault DETAIL : No cache finded')

    print("Vault DETAIL : DL used ", cache_key)

    # Sinon, effectuer la requête
    payload = {"type": "vaultDetails", "user": leader, "vaultAddress": vault_address}
    response = requests.post(INFO_URL, json=payload)
    if response.status_code == 200:
        details = response.json()
        with open(local_DETAILS_CACHE_FILE, "w") as f:
            json.dump(details, f)
        return details
    else:
        return None