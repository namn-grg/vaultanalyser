import requests
import os
import json
from datetime import datetime, timedelta
import streamlit as st


# URL pour les vaults
VAULTS_URL = "https://stats-data.hyperliquid.xyz/Mainnet/vaults"
INFO_URL = "https://api-ui.hyperliquid.xyz/info"
CACHE_FILE = "vaults_cache.json"
DETAILS_CACHE_FILE = "vault_details_cache.json"

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
            last_update = datetime.fromisoformat(cache["last_update"])
            if datetime.now() - last_update < timedelta(days=CACHE_DAYS_VALIDITY):
                print("Vault list CACHED USED")
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
                "Created Date": datetime.fromtimestamp(vault["summary"]["createTimeMillis"] / 1000).strftime("%d/%m/%Y"),
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

    st.toast("Vault list OK !", icon="✅")


    return vaults

def fetch_vault_details(leader, vault_address):
    """Récupère les détails d'une vault avec un système de cache."""
    try:
        with open(DETAILS_CACHE_FILE, "r") as f:
            details_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        details_cache = {}

    cache_key = f"{leader}_{vault_address}"  # Identifiant unique pour chaque vault
    # Vérifier si la valeur est déjà en cache
    if cache_key in details_cache:
        print("Vault DETAIL : EXIST ", cache_key)
        cached_entry = details_cache[cache_key]
        last_update = datetime.fromisoformat(cached_entry["last_update"])
        if datetime.now() - last_update < timedelta(days=CACHE_DAYS_VALIDITY):  # Cache valide pendant 1 jour
            print("Vault DETAIL : cache used ", cache_key)
            return cached_entry["data"]
        else:
            print("Vault DETAIL : Bad timestamp, DL required")

    print("Vault DETAIL : DL used ", cache_key)

    # Sinon, effectuer la requête
    payload = {"type": "vaultDetails", "user": leader, "vaultAddress": vault_address}
    response = requests.post(INFO_URL, json=payload)
    if response.status_code == 200:
        details = response.json()
        # Mettre à jour le cache
        details_cache[cache_key] = {
            "last_update": datetime.now().isoformat(), 
            "data": details
        }
        with open(DETAILS_CACHE_FILE, "w") as f:
            json.dump(details_cache, f)
        return details
    else:
        return None