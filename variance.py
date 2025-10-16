import streamlit as st
import pandas as pd

# ===========================================================
# --- PAGE CONFIG ---
# ===========================================================
st.set_page_config(page_title="Item Margin Range Analysis", layout="wide")

# ===========================================================
# --- LOAD DATA ---
# ===========================================================
file_path = "oud mehta sales.Xlsx"  # update if needed

# Load without header first to find the correct header row
df_raw = pd.read_excel(file_path, header=None)

# Detect header row (search for "Item Code")
header_row = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains("Item Code", case=False).any(), axis=1)].index[0]

# Reload with proper header
df = pd.read_excel(file_path, header=header_row)

# ===========================================================
# --- CHECK REQUIRED COLUMNS ---
# ===========================================================
required_cols = ["Item Code", "Items", "Qty Sold", "Total Cost", "Total Sales", "Total Profit", "Excise Margin (%)"]
missing = [col for col in required_cols if col not in df.columns]
if missing:
    st.error(f"❌ Missing columns: {missing}")
    st.stop()

# Convert numeric columns
for col in ["Qty Sold", "Total Cost", "Total Sales", "Total Profit", "Excise Margin (%)"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ===========================================================
# --- DERIVED METRICS ---
# ===========================================================
# Calculate cost per item (Unit Cost)
df["Unit Cost"] = df["Total Cost"] / df["Qty Sold"]

# Classify margin ranges
def classify_margin(m):
    if m < 5:
        return "< 5%"
    elif 5 <= m < 10:
        return "5% - 10%"
    elif 10 <= m < 20:
        return "10% - 20%"
    elif 20 <= m < 30:
        return "20% - 30%"
    else:
        return "> 30%"

df["Margin Range"] = df["Excise Margin (%)"].apply(classify_margin)

# ===========================================================
# --- STREAMLIT DISPLAY ---
# ===========================================================
st.title("📊 Item Margin Range Analysis")

# Dropdown filter for ranges
ranges = df["Margin Range"].unique().tolist()
ranges.sort(key=lambda x: float(x.split("%")[0].replace("<", "").replace(">", "").split("-")[0]))  # sort properly

selected_range = st.selectbox("🔍 Select Margin Range:", ["All"] + ranges)

# Filter data
if selected_range != "All":
    filtered_df = df[df["Margin Range"] == selected_range]
else:
    filtered_df = df.copy()

# Simulate +3% and +4% price increases
for inc in [0.03, 0.04]:
    filtered_df[f"Profit +{int(inc*100)}% Price"] = filtered_df["Total Profit"] + (filtered_df["Total Sales"] * inc)
    filtered_df[f"Change in Profit +{int(inc*100)}%"] = filtered_df[f"Profit +{int(inc*100)}% Price"] - filtered_df["Total Profit"]

# ===========================================================
# --- DISPLAY DATA TABLE ---
# ===========================================================
st.subheader(f"📦 Items in Margin Range: {selected_range}")

st.dataframe(
    filtered_df[
        [
            "Item Code", "Items", "Qty Sold", "Unit Cost", "Total Cost", "Total Sales",
            "Total Profit", "Excise Margin (%)", "Margin Range",
            "Profit +3% Price", "Change in Profit +3%", "Profit +4% Price", "Change in Profit +4%"
        ]
    ],
    use_container_width=True
)

# ===========================================================
# --- INSIGHTS SECTION ---
# ===========================================================
total_current_profit = filtered_df["Total Profit"].sum()
total_profit_3 = filtered_df["Profit +3% Price"].sum()
total_profit_4 = filtered_df["Profit +4% Price"].sum()
avg_margin = filtered_df["Excise Margin (%)"].mean()
avg_unit_cost = filtered_df["Unit Cost"].mean()

st.subheader("📈 Insights")
st.write(f"✅ **Average Margin:** {avg_margin:.2f}%")
st.write(f"💰 **Average Unit Cost:** {avg_unit_cost:,.2f}")
st.write(f"💵 **Total Current Profit:** {total_current_profit:,.2f}")
st.write(f"📈 **Profit if +3% price:** {total_profit_3:,.2f} (Change: {total_profit_3 - total_current_profit:,.2f})")
st.write(f"📈 **Profit if +4% price:** {total_profit_4:,.2f} (Change: {total_profit_4 - total_current_profit:,.2f})")

# ===========================================================
# --- OVERALL SUMMARY BY MARGIN RANGE ---
# ===========================================================
st.subheader("📘 Summary by Margin Range")

summary = (
    df.groupby("Margin Range")
    .agg(
        Total_Items=("Item Code", "count"),
        Total_Sales=("Total Sales", "sum"),
        Total_Profit=("Total Profit", "sum"),
        Avg_Margin=("Excise Margin (%)", "mean"),
        Avg_Unit_Cost=("Unit Cost", "mean")
    )
    .reset_index()
)

st.dataframe(summary, use_container_width=True)
