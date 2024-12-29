import requests
import os
import json
import re
from datetime import datetime
import streamlit as st


# URL for the vaults
VAULTS_URL = "https://stats-data.hyperliquid.xyz/Mainnet/vaults"
INFO_URL = "https://api-ui.hyperliquid.xyz/info"

CACHE_DIR = "./cache/"

CACHE_FILE = CACHE_DIR + "vaults_cache.json"
DETAILS_CACHE_FILE = CACHE_DIR + "/vault_detail/#KEY#/vault_details_cache.json"


CACHE_DAYS_VALIDITY = 7


def fetch_vaults_data():
    """Fetches vault data (with cache)."""

    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text(f"Downloading vault list...")

    cache_used = False

    # Cache already exist?
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            cache_used = True
            vaults = cache["data"]
    except (FileNotFoundError, KeyError, ValueError):
        pass

    if not cache_used:  # Cache does not exist
        response = requests.get(VAULTS_URL)
        data = response.json()

        # Step 2: Prepare vault data
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
            json.dump(
                {"last_update": datetime.now().isoformat(), "data": vaults}, f)

    progress_bar.progress(100)  # Progress bar (from 0 to 1)
    if cache_used:
        status_text.text(f"Vault List cache used")
    else:
        status_text.text(f"Fresh vault List downloaded")

    progress_bar.empty()
    status_text.empty()

    if not cache_used:
        st.toast("Vault list OK!", icon="✅")

    return vaults


def fetch_vault_details(leader, vault_address):
    """Fetches vault details with a caching system."""

    cache_key = re.sub(r"[^a-zA-Z0-9_]", "", leader + "_" + vault_address)
    local_DETAILS_CACHE_FILE = DETAILS_CACHE_FILE.replace('#KEY#', cache_key)

    # Extract the directory path without the file
    directory_path = os.path.dirname(local_DETAILS_CACHE_FILE)

    # Create directories if needed
    os.makedirs(directory_path, exist_ok=True)

    try:
        with open(local_DETAILS_CACHE_FILE, "r") as f:
            # print("Vault DETAIL: cache used", cache_key)
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print('Vault DETAIL: No cache found')

    print("Vault DETAIL: Download used", cache_key)

    # Otherwise, make the request
    payload = {"type": "vaultDetails",
               "user": leader, "vaultAddress": vault_address}
    response = requests.post(INFO_URL, json=payload)
    if response.status_code == 200:
        details = response.json()
        with open(local_DETAILS_CACHE_FILE, "w") as f:
            json.dump(details, f)
        return details
    else:
        return None
