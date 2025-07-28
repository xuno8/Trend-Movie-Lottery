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

    # Blacklist configuration
    st.sidebar.header("Blacklist Configuration")
    blacklist_input = st.sidebar.text_area(
        "Enter email addresses to blacklist (one per line):",
        height=100,
        help="Enter email addresses that should be excluded from the lottery, one per line"
    )
    
    # Process blacklist emails
    blacklist_emails = []
    if blacklist_input.strip():
        blacklist_emails = [
            email.strip().lower() 
            for email in blacklist_input.strip().split('\n') 
            if email.strip() and '@' in email.strip()
        ]
        # Remove duplicates while preserving order
        blacklist_emails = list(dict.fromkeys(blacklist_emails))
        
        if blacklist_emails:
            st.sidebar.info(f"📝 Blacklist: {len(blacklist_emails)} emails")
            with st.sidebar.expander("View blacklisted emails"):
                for email in blacklist_emails:
                    st.write(f"• {email}")
        else:
            st.sidebar.warning("⚠️ No valid emails found in blacklist")

    # Button to run lottery
    if st.sidebar.button("Run Lottery"):
        winners = {opt: [] for opt in all_options}
        available_idx = set(df.index)
        
        # Filter out blacklisted users
        blacklisted_idx = []
        if blacklist_emails:
            df_emails_lower = df['Email'].str.lower()
            blacklisted_mask = df_emails_lower.isin(blacklist_emails)
            blacklisted_idx = df[blacklisted_mask].index.tolist()
            available_idx -= set(blacklisted_idx)

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
        
        # Display blacklist statistics
        if blacklisted_idx:
            st.write("## 🚫 黑名單統計")
            blacklisted_count = len(blacklisted_idx)
            blacklisted_tickets = df.loc[blacklisted_idx, '登記票數 Number of tickets'].sum()
            st.write(f"**被排除人數: {blacklisted_count}**")
            st.write(f"**被排除票數: {blacklisted_tickets}**")
            st.write("---")
        
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
        tab_names = all_options + ["Losers", "Violations"]
        if blacklisted_idx:
            tab_names.append("Blacklisted")
        tabs = st.tabs(tab_names)
        for idx, opt in enumerate(tab_names):
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
                elif opt == "Blacklisted":
                    subset = df.loc[blacklisted_idx]
                    st.write("### 黑名單統計")
                    st.write(f"被排除人數: {len(subset)}")
                    st.write(f"被排除票數: {subset['登記票數 Number of tickets'].sum()}")
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
            if blacklisted_idx:
                df.loc[blacklisted_idx, display_cols].to_excel(writer, sheet_name="Blacklisted", index=False)
        processed_data = output.getvalue()

        st.download_button(
            label="Download results as Excel",
            data=processed_data,
            file_name="lottery_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.sidebar.info("Set the maximum number of winners for each session and click 'Run Lottery'.")
