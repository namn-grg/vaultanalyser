# source .venv/bin/activate
# streamlit run main.py

#
#       @TODO : les indicateurs https://www.codearmo.com/blog/sharpe-sortino-and-calmar-ratios-python
#       @TODO : avoir un système de blocage si plusieurs personnes demandent en même temps
#       
#
#
#
import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta

st.set_page_config(layout="wide")  # Page en full largeur

# URL pour les vaults
VAULTS_URL = "https://stats-data.hyperliquid.xyz/Mainnet/vaults"
INFO_URL = "https://api-ui.hyperliquid.xyz/info"
CACHE_FILE = "vaults_cache.json"
DETAILS_CACHE_FILE = "vault_details_cache.json"

def fetch_vaults_data(): 
    """Récupère les données des vaults (avec cache)."""
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            last_update = datetime.fromisoformat(cache["last_update"])
            if datetime.now() - last_update < timedelta(days=1):
                print("Vault list CACHED USED")
                return cache["data"]
    except (FileNotFoundError, KeyError, ValueError):
        pass
    print("Vault list DOWNLOADED")
    response = requests.get(VAULTS_URL)
    data = response.json()
    with open(CACHE_FILE, "w") as f:
        json.dump({"last_update": datetime.now().isoformat(), "data": data}, f)
    return data

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
        if datetime.now() - last_update < timedelta(days=1):  # Cache valide pendant 1 jour
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

def calculate_performance_metrics(pnl_history, risk_free_rate=0.0):
    """
    Calculate comprehensive performance metrics for a vault with robust drawdown calculation.
    """
    # Ensure we have enough data
    if not pnl_history or len(pnl_history) < 2:
        return {
            "Sortino Ratio": None,
            "Sharpe Ratio": None,
            "Max Drawdown %": None,
            "Calmar Ratio": None
        }
    
    try:
        # Extract PNL values
        pnl_values = np.array([float(pnl[1]) for pnl in pnl_history])
        
        # Calculate periodic returns with safe method
        returns = np.zeros_like(pnl_values[1:])
        for i in range(1, len(pnl_values)):
            if pnl_values[i-1] != 0:
                returns[i-1] = (pnl_values[i] - pnl_values[i-1]) / pnl_values[i-1]
        
        # Remove potential infinite or NaN values
        returns = returns[np.isfinite(returns)]
        
        if len(returns) == 0:
            return {
                "Sortino Ratio": 0,
                "Sharpe Ratio": 0,
                "Max Drawdown %": 0,
                "Calmar Ratio": 0
            }
        
        # Sharpe Ratio Calculation
        avg_return = np.mean(returns)
        std_dev = np.std(returns)
        
        # Safe Sharpe Ratio calculation
        sharpe_ratio = (avg_return - risk_free_rate/252) / std_dev if std_dev > 0 else 0
        
        # Sortino Ratio Calculation
        negative_returns = returns[returns < 0]
        downside_deviation = np.std(negative_returns) if len(negative_returns) > 0 else 0
        sortino_ratio = (avg_return - risk_free_rate/252) / downside_deviation if downside_deviation > 0 else 0
        
        # Max Drawdown Calculation - More Robust Method
        cumulative_value = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_value)
        drawdown = (cumulative_value - running_max) / running_max * 100
        max_drawdown = np.min(drawdown)
        
        # Annualized Return Calculation for Calmar Ratio
        # Using geometric mean of returns
        annualized_return = (np.prod(1 + returns) ** (252 / len(returns)) - 1) * 100
        
        # Calmar Ratio Calculation
        calmar_ratio = annualized_return / abs(max_drawdown) if abs(max_drawdown) > 0 else 0
        
        return {
            "Sortino Ratio": round(sortino_ratio, 3),
            "Sharpe Ratio": round(sharpe_ratio, 3),
            "Max Drawdown %": round(max_drawdown, 2),
            "Calmar Ratio": round(calmar_ratio, 3)
        }
    
    except Exception as e:
        print(f"Error in performance metrics calculation: {e}")
        return {
            "Sortino Ratio": None,
            "Sharpe Ratio": None,
            "Max Drawdown %": None,
            "Calmar Ratio": None
        }

# Étape 1 : Récupération des données des vaults
data = fetch_vaults_data()

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

# Limiter à 50 premières vaults
vaults = vaults[:50]

# Étape 3 : Collecter les historiques PNL pour chaque vault et calculer les indicateurs
indicators = []
for vault in vaults:
    details = fetch_vault_details(vault["Leader"], vault["Vault"])
    if details and "portfolio" in details and len(details["portfolio"]) > 3:
        pnl_history = details["portfolio"][3][1].get("pnlHistory", [])
        metrics = calculate_performance_metrics(pnl_history)
        indicator_row = {
            "Name": vault["Name"], 
            **metrics  # Unpacks the metrics dictionary
        }
        indicators.append(indicator_row)
    else:
        indicators.append({
            "Name": vault["Name"], 
            "Sortino Ratio": None,
            "Sharpe Ratio": None,
            "Max Drawdown %": None,
            "Calmar Ratio": None
        })

# Étape 4 : Fusionner les indicateurs avec le tableau principal
indicators_df = pd.DataFrame(indicators)
vaults_df = pd.DataFrame(vaults)
del vaults_df['Leader']
final_df = vaults_df.merge(indicators_df, on="Name", how="left")

# Afficher le tableau
st.title(f"Liste des Vaults Actives ({len(final_df)}) Vaults")
st.write(final_df)