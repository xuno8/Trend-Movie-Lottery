import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

# Title of the Streamlit app
st.set_page_config(page_title="Trend Movie Lottery Draw")
st.title("Trend Movie Lottery Draw")

# Upload CSV
uploaded_file = st.file_uploader("Upload registration CSV", type=["csv"])

if uploaded_file is not None:
    # Read CSV
    df = pd.read_csv(uploaded_file)

    # Preferences columns
    prefs_cols = ["第一志願", "第二志願", "第三志願", "第四志願"]

    # Remove duplicate preferences per user
    def clean_preferences(row):
        seen = []
        for pref in row[prefs_cols]:
            if pd.isna(pref):
                continue
            if pref not in seen:
                seen.append(pref)
        return seen

    df["cleaned_prefs"] = df.apply(clean_preferences, axis=1)

    # Identify all unique options
    all_options = sorted({opt for prefs in df["cleaned_prefs"] for opt in prefs})

    st.sidebar.header("Configure max winners per option")
    max_winners = {}
    for opt in all_options:
        max_winners[opt] = st.sidebar.number_input(
            f"Maximum winners for '{opt}'", min_value=0, value=1, step=1
        )

    # Button to run lottery
    if st.sidebar.button("Run Lottery"):
        winners = {opt: [] for opt in all_options}
        available_idx = set(df.index)

        # Lottery by preference order
        for pref_level in range(len(prefs_cols)):
            for opt in all_options:
                candidates = [i for i in available_idx if len(df.at[i, "cleaned_prefs"]) > pref_level
                              and df.at[i, "cleaned_prefs"][pref_level] == opt]
                slots = max_winners[opt] - len(winners[opt])
                k = min(len(candidates), slots)
                if k > 0:
                    selected = list(np.random.choice(candidates, size=k, replace=False))
                    winners[opt].extend(selected)
                    available_idx -= set(selected)

        losers = list(available_idx)

        # Prepare columns to display and export
        display_cols = ["Email", "Name", "PSID", "登記票數 Number of tickets"] + prefs_cols

        # Display results in tabs
        tabs = st.tabs(all_options + ["Losers"])
        for idx, opt in enumerate(all_options + ["Losers"]):
            with tabs[idx]:
                if opt == "Losers":
                    subset = df.loc[losers]
                else:
                    subset = df.loc[winners[opt]]
                st.write(subset[display_cols])

        # Export to Excel with multiple sheets
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for opt in all_options:
                safe_name = re.sub(r"[\\/*?:\[\]]", "_", opt)[:31]
                df.loc[winners[opt], display_cols].to_excel(writer, sheet_name=safe_name, index=False)
            df.loc[losers, display_cols].to_excel(writer, sheet_name="Losers", index=False)
        processed_data = output.getvalue()

        st.download_button(
            label="Download results as Excel",
            data=processed_data,
            file_name="lottery_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.sidebar.info("Set the maximum number of winners for each session and click 'Run Lottery'.")
