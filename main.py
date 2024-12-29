# source .venv/bin/activate
# streamlit run main.py


import json
import os
from datetime import datetime

import pandas as pd

import streamlit as st

from hyperliquid.vaults import fetch_vault_details, fetch_vaults_data
from metrics.drawdown import (
    calculate_max_drawdown_on_accountValue,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
)


def check_date_file_exists(directory="./cache"):
    """
    Checks if the `date.json` file exists in the specified directory.

    :param directory: Directory where the file is expected to be located (default: /cache).
    :return: True if the file exists, otherwise False.
    """
    # Full file path
    file_path = os.path.join(directory, "date.json")

    # Check existence
    return os.path.exists(file_path)


def create_date_file(directory="./cache"):
    """
    Creates a `date.json` file in the specified directory with the current date.

    :param directory: Directory where the file will be created (default: /cache).
    """
    # Ensure the directory exists
    os.makedirs(directory, exist_ok=True)

    # Full file path
    file_path = os.path.join(directory, "date.json")

    # Content to write
    current_date = {"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    # Write to the file
    with open(file_path, "w") as file:
        json.dump(current_date, file, indent=4)
    print(f"`date.json` file created in {file_path}")


def read_date_file(directory="./cache"):
    """
    Reads and returns the date saved in the `date.json` file from the specified directory.

    :param directory: Directory where the file is located (default: /cache).
    :return: The date as a string or None if the file doesn't exist.
    """
    # Full file path
    file_path = os.path.join(directory, "date.json")

    # Check if the file exists
    if not os.path.exists(file_path):
        print("`date.json` file not found.")
        return None

    # Read the file
    with open(file_path, "r") as file:
        data = json.load(file)
        return data.get("date")


# Layout for 3 columns


def slider_with_label(label, col, min_value, max_value, default_value, step, key):
    """Create a slider with a custom centered title."""
    col.markdown(
        f"<h3 style='text-align: center;'>{label}</h3>", unsafe_allow_html=True)
    if not min_value < max_value:
        col.markdown(
            f"<p style='text-align: center;'>No choice available ({min_value} for all)</p>", unsafe_allow_html=True
        )
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
    Calculates the average daily gain percentage.

    :param rebuilded_pnl: List of cumulative PnL values ($).
    :param days_since: Number of days (int).
    :return: Average daily gain percentage (float).
    """
    if len(rebuilded_pnl) < 2 or days_since <= 0:
        return 0  # Not enough data to calculate

    initial_value = rebuilded_pnl[0]
    final_value = rebuilded_pnl[-1]

    # Avoid division by zero
    if initial_value == 0:
        return 0  # Cannot calculate if the initial value is 0

    average_daily_gain_pct = (
        (final_value - initial_value) / (initial_value * days_since)) * 100
    return average_daily_gain_pct


def calculate_total_gain_percentage(rebuilded_pnl):
    """
    Calculates the total percentage change since the beginning.

    :param rebuilded_pnl: List of cumulative PnL values ($).
    :return: Total percentage change (float).
    """
    if len(rebuilded_pnl) < 2:
        return 0  # Not enough data to calculate

    initial_value = rebuilded_pnl[0]
    final_value = rebuilded_pnl[-1]

    # Avoid division by zero
    if initial_value == 0:
        return 0  # Cannot calculate if the initial value is 0

    total_gain_pct = ((final_value - initial_value) / initial_value) * 100
    return total_gain_pct


limit_vault = False
# limit_vault = True


st.set_page_config(layout="wide")  # Full-width page layout

if not check_date_file_exists():
    create_date_file()

data_date = read_date_file()

st.markdown(
    f"<h3 style='text-align: center;'>Data downloaded {data_date} </h3>", unsafe_allow_html=True)


DATAFRAME_CACHE_FILE = "./cache/dataframe.pkl"

cache_used = False
try:
    final_df = pd.read_pickle(DATAFRAME_CACHE_FILE)
    cache_used = True
except (FileNotFoundError, KeyError, ValueError):
    pass

if not cache_used:

    # Step 1: Fetch vault data
    vaults = fetch_vaults_data()

    # Limit to the first 50 vaults
    if limit_vault:
        vaults = vaults[:50]

    # Step 3: Collect PnL histories for each vault and calculate indicators

    progress_bar = st.progress(0)  # Progress bar (from 0 to 1)
    status_text = st.empty()  # Text displaying status
    status_text.text(f"Downloading vault details...")
    total_steps = len(vaults)
    indicators = []
    progress_i = 1
    for vault in vaults:

        vault_to_log = ""  # "0x9c823dab050a2b6f0b549d89b8f0b909f6936a92"

        details = fetch_vault_details(vault["Leader"], vault["Vault"])

        if vault["Vault"] == vault_to_log:
            print("")
            print("----- ", vault["Vault"])

        progress_bar.progress(progress_i / total_steps)
        progress_i = progress_i + 1
        status_text.text(
            f"Downloading vault details ({progress_i}/{total_steps})...")

        nb_followers = 0
        if details and "followers" in details:
            for idx, value in enumerate(details["followers"]):
                if float(value["vaultEquity"]) >= 0.01:
                    nb_followers = nb_followers + 1

        if details and "portfolio" in details:

            if details["portfolio"][3][0] == "allTime":
                data_source_pnlHistory = details["portfolio"][3][1].get(
                    "pnlHistory", [])
                data_source_accountValueHistory = details["portfolio"][3][1].get(
                    "accountValueHistory", [])
                rebuilded_pnl = []

                balance = start_balance_amount = 1000000
                nb_rekt = 0
                last_rekt_idx = -10

                # Recalculate the balance without considering deposit movements
                for idx, value in enumerate(data_source_pnlHistory):
                    if idx == 0:
                        continue

                    # Capital at time T
                    final_capital = float(
                        data_source_accountValueHistory[idx][1])
                    # Cumulative PnL at time T
                    final_cumulated_pnl = float(data_source_pnlHistory[idx][1])
                    # Cumulative PnL at time T -1
                    previous_cumulated_pnl = float(
                        data_source_pnlHistory[idx - 1][1]) if idx > 0 else 0
                    # Non-cumulative PnL at time T
                    final_pnl = final_cumulated_pnl - previous_cumulated_pnl
                    # Capital before the gain/loss
                    initial_capital = final_capital - final_pnl

                    if initial_capital <= 0:
                        if last_rekt_idx + 1 != idx:
                            rebuilded_pnl = []
                            balance = start_balance_amount
                            nb_rekt = nb_rekt + 1
                        last_rekt_idx = idx
                        continue
                    # Gain/loss ratio
                    ratio = final_capital / initial_capital

                    # Verify timestamp consistency
                    if data_source_pnlHistory[idx][0] != data_source_accountValueHistory[idx][0]:
                        print("Just to check, normally not happening")
                        exit()

                    # Update the simulated balance
                    balance = balance * ratio

                    rebuilded_pnl.append(balance)

                metrics = {
                    "Max DD %": calculate_max_drawdown_on_accountValue(rebuilded_pnl),
                    "Rekt": nb_rekt,
                    "Act. Followers": nb_followers,
                    "Sharpe Ratio": calculate_sharpe_ratio(rebuilded_pnl),
                    "Sortino Ratio": calculate_sortino_ratio(rebuilded_pnl),
                    "Av. Daily Gain %": calculate_average_daily_gain(rebuilded_pnl, vault["Days Since"]),
                    "Gain %": calculate_total_gain_percentage(rebuilded_pnl),
                }
                # Unpacks the metrics dictionary
                indicator_row = {"Name": vault["Name"], **metrics}
                indicators.append(indicator_row)

    progress_bar.empty()
    status_text.empty()

    st.toast("Vault details OK!", icon="✅")

    # Step 4: Merge indicators with the main table
    indicators_df = pd.DataFrame(indicators)
    vaults_df = pd.DataFrame(vaults)
    del vaults_df["Leader"]
    final_df = vaults_df.merge(indicators_df, on="Name", how="left")

    final_df.to_pickle(DATAFRAME_CACHE_FILE)


# Filters
st.subheader(f"Vaults available ({len(final_df)})")
filtered_df = final_df


# Filter by 'Name' (last filter, free text)
st.markdown("<h3 style='text-align: center;'>Filter by Name</h3>",
            unsafe_allow_html=True)
name_filter = st.text_input(
    "Name Filter", "", placeholder="Enter names separated by ',' to filter (e.g., toto,tata)...", key="name_filter"
)

# Apply the filter
if name_filter.strip():  # Check that the filter is not empty
    name_list = [name.strip() for name in name_filter.split(",")
                 ]  # List of names to search for
    pattern = "|".join(name_list)  # Create a regex pattern with logical "or"
    filtered_df = filtered_df[filtered_df["Name"].str.contains(
        pattern, case=False, na=False, regex=True)]

# Organize sliders into rows of 3
sliders = [
    {"label": "Min Sharpe Ratio", "column": "Sharpe Ratio",
        "max": False, "default": 0.4, "step": 0.1},
    {"label": "Min Sortino Ratio", "column": "Sortino Ratio",
        "max": False, "default": 0.5, "step": 0.1},
    {"label": "Max Rekt accepted", "column": "Rekt",
        "max": True, "default": 0, "step": 1},
    {"label": "Max DD % accepted", "column": "Max DD %",
        "max": True, "default": 15, "step": 1},
    {"label": "Min Days Since accepted", "column": "Days Since",
        "max": False, "default": 100, "step": 1},
    {"label": "Min TVL accepted", "column": "Total Value Locked",
        "max": False, "default": 0, "step": 1},
    {"label": "Min APR accepted", "column": "APR %",
        "max": False, "default": 0, "step": 1},
    {"label": "Min Followers", "column": "Act. Followers",
        "max": False, "default": 0, "step": 1},
]

for i in range(0, len(sliders), 3):
    cols = st.columns(3)
    for slider, col in zip(sliders[i: i + 3], cols):
        column = slider["column"]
        value = slider_with_label(
            slider["label"],
            col,
            min_value=float(filtered_df[column].min()),
            max_value=float(filtered_df[column].max()),
            default_value=float(slider["default"]),
            step=float(slider["step"]),
            key=f"slider_{column}",
        )
        if not value == None:
            if slider["max"]:
                filtered_df = filtered_df[filtered_df[column] <= value]
            else:
                filtered_df = filtered_df[filtered_df[column] >= value]

# Display the table
st.title(f"Vaults filtered ({len(filtered_df)}) ")

# Add a column with clickable links
filtered_df["Link"] = filtered_df["Vault"].apply(
    lambda vault: f"https://app.hyperliquid.xyz/vaults/{vault}")

# Reset index for continuous ranking
filtered_df = filtered_df.reset_index(drop=True)


st.dataframe(
    filtered_df,
    use_container_width=True,
    # Adjust height based on the number of rows
    height=(len(filtered_df) * 35) + 50,
    column_config={
        "Link": st.column_config.LinkColumn(
            "Vault Link",
            display_text="Vault Link",
        )
    },
)
