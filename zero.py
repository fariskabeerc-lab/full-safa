import streamlit as st
import pandas as pd
from io import BytesIO

# ==========================================================
# PAGE SETUP
# ==========================================================
st.set_page_config(page_title="📦 Inventory Zero-Sales Report", layout="wide")
st.title("📊 Inventory Zero-Sales & Missing Variance Dashboard")

# ==========================================================
# LOAD EXCEL FILES DIRECTLY
# ==========================================================
inventory_path = "zero sales(1).xlsx"        # Inventory file
variance_path = "sao variance.Xlsx"         # Stock variance file

# Read Excel files
df_inventory = pd.read_excel(inventory_path)
df_variance = pd.read_excel(variance_path)

# ==========================================================
# DATA PREPARATION
# ==========================================================
# Rename for consistency
df_variance.rename(columns={"Barcode": "Item Bar Code"}, inplace=True)

# Ensure barcodes are strings
df_inventory["Item Bar Code"] = df_inventory["Item Bar Code"].astype(str)
df_variance["Item Bar Code"] = df_variance["Item Bar Code"].astype(str)

# Merge data — keep all inventory items
merged = pd.merge(
    df_inventory,
    df_variance[["Item Bar Code", "Book Stock"]],
    on="Item Bar Code",
    how="left"
)

# ==========================================================
# TOTAL INVENTORY VALUE
# ==========================================================
total_inventory_value = df_inventory["Stock Value"].sum()
st.subheader("📌 Inventory Summary")
st.write(f"**Total inventory value (Zero Sales Items):** {total_inventory_value}")
st.write("Note: All items in this inventory have zero sales.")

# ==========================================================
# ITEMS NOT FOUND IN VARIANCE
# ==========================================================
missing_variance_items = merged[merged["Book Stock"].isna()].copy()
missing_variance_items.fillna("Not Found in Variance", inplace=True)

# Total value of missing variance items
total_missing_value = missing_variance_items["Stock Value"].sum()

st.subheader(f"📋 Items in Inventory but Not Found in Stock Variance (Total Value: {total_missing_value})")
st.dataframe(missing_variance_items, use_container_width=True)

# ==========================================================
# DOWNLOAD MERGED RESULT
# ==========================================================
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventory_Report")
    return output.getvalue()

excel_data = to_excel(merged)
st.download_button(
    label="📥 Download Inventory Report",
    data=excel_data,
    file_name="Inventory_Zero_Sales_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
