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

    # Dynamically detect preferences columns
    possible_prefs = ["第一志願", "第二志願", "第三志願", "第四志願"]
    prefs_cols = []
    
    # Check for exact matches first, then partial matches
    for pref in possible_prefs:
        # First try exact match
        if pref in df.columns:
            prefs_cols.append(pref)
        else:
            # Then try partial match (e.g., "第一志願 First Preference")
            matching_cols = [col for col in df.columns if pref in col]
            if matching_cols:
                prefs_cols.append(matching_cols[0])  # Take the first match
    
    if not prefs_cols:
        st.error("找不到志願欄位！請確認 CSV 檔案包含 '第一志願', '第二志願' 等欄位。")
        st.stop()
    
    st.info(f"檢測到 {len(prefs_cols)} 個志願欄位: {', '.join(prefs_cols)}")

    # Remove duplicate preferences per user
    def clean_preferences(row):
        seen = []
        violations = []
        for pref in row[prefs_cols]:
            if pd.isna(pref):
                continue
            if pref not in seen:
                seen.append(pref)
            else:
                violations.append(pref)
        return seen, violations

    # Apply the function and create new columns
    result_df = pd.DataFrame(df.apply(clean_preferences, axis=1).tolist(), index=df.index, columns=['cleaned_prefs', 'violations'])
    df = pd.concat([df, result_df], axis=1)

    # Identify all unique options
    all_options = sorted({opt for prefs in df["cleaned_prefs"] for opt in prefs})

    st.sidebar.header("Configure max winners per option")
    max_winners = {}
    ticket_prices = {}
    for opt in all_options:
        max_winners[opt] = st.sidebar.number_input(
            f"Maximum winners for '{opt}'", min_value=0, value=1, step=1
        )
        ticket_prices[opt] = st.sidebar.number_input(
            f"Ticket price for '{opt}' (NT$)", min_value=0, value=300, step=1
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

        # Calculate total cost
        total_overall_cost = sum(len(winners[opt]) * ticket_prices[opt] for opt in all_options)
        
        # Display overall cost summary
        st.write("## 💰 總花費統計")
        st.write(f"**整體總花費: NT${total_overall_cost:,}**")
        
        # Display individual costs
        st.write("### 各志願花費明細:")
        for opt in all_options:
            winner_count = len(winners[opt])
            cost = winner_count * ticket_prices[opt]
            st.write(f"- **{opt}**: {winner_count} 人 × NT\\${ticket_prices[opt]:,} = **NT\\${cost:,}**")
        
        st.write("---")

        # Prepare columns to display and export
        display_cols = ["Email", "Name", "PSID", "登記票數 Number of tickets"] + prefs_cols

        # Display results in tabs
        tabs = st.tabs(all_options + ["Losers", "Violations"])
        for idx, opt in enumerate(all_options + ["Losers", "Violations"]):
            with tabs[idx]:
                if opt == "Losers":
                    subset = df.loc[losers]
                    st.write("### 未中獎人數統計")
                    st.write(f"總人數: {len(subset)}")
                    st.write(f"總票數: {subset['登記票數 Number of tickets'].sum()}")
                elif opt == "Violations":
                    subset = df[df["violations"].str.len() > 0]
                    st.write("### 違規人數統計")
                    st.write(f"總人數: {len(subset)}")
                    st.write(f"總票數: {subset['登記票數 Number of tickets'].sum()}")
                else:
                    subset = df.loc[winners[opt]]
                    winner_count = len(subset)
                    total_cost = winner_count * ticket_prices[opt]
                    st.write(f"### {opt} 中獎統計")
                    st.write(f"中獎人數: {winner_count}")
                    st.write(f"中獎總票數: {subset['登記票數 Number of tickets'].sum()}")
                    st.write(f"票價: NT${ticket_prices[opt]:,}")
                    st.write(f"**總花費: NT${total_cost:,}**")
                st.write(subset[display_cols])

        # Export to Excel with multiple sheets
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for opt in all_options:
                safe_name = re.sub(r"[\\/*?:\[\]]", "_", opt)[:31]
                df.loc[winners[opt], display_cols].to_excel(writer, sheet_name=safe_name, index=False)
            df.loc[losers, display_cols].to_excel(writer, sheet_name="Losers", index=False)
            df[df["violations"].str.len() > 0][display_cols].to_excel(writer, sheet_name="Violations", index=False)
        processed_data = output.getvalue()

        st.download_button(
            label="Download results as Excel",
            data=processed_data,
            file_name="lottery_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.sidebar.info("Set the maximum number of winners for each session and click 'Run Lottery'.")
