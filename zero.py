import streamlit as st
import pandas as pd
from io import BytesIO

# ==========================================================
# PAGE SETUP
# ==========================================================
st.set_page_config(page_title="📦 Inventory vs Stock Variance", layout="wide")
st.title("📊 Inventory & Stock Variance Comparison Dashboard")

# ==========================================================
# LOAD EXCEL FILES DIRECTLY (EDIT PATHS HERE)
# ==========================================================
inventory_path = "zero sales(1).xlsx"        # Inventory file
variance_path = "sao variance.Xlsx"         # Stock variance file

# Read both Excel files
df_inventory = pd.read_excel(inventory_path)
df_variance = pd.read_excel(variance_path)

# ==========================================================
# DATA PREPARATION
# ==========================================================
# Rename to keep the same column key
df_variance.rename(columns={"Barcode": "Item Bar Code"}, inplace=True)

# Ensure barcodes are strings
df_inventory["Item Bar Code"] = df_inventory["Item Bar Code"].astype(str)
df_variance["Item Bar Code"] = df_variance["Item Bar Code"].astype(str)

# Merge data — keep all inventory items
merged = pd.merge(
    df_inventory,
    df_variance[
        [
            "Item Bar Code",
            "Book Stock",
            "Phys Stock",
            "Diff Stock",
            "Book Value",
            "Phys Value",
            "Diff Value",
        ]
    ],
    on="Item Bar Code",
    how="left",
)

# Fill missing variance data with 0
for col in ["Book Stock", "Phys Stock", "Diff Stock", "Book Value", "Phys Value", "Diff Value"]:
    if col in merged.columns:
        merged[col] = merged[col].fillna(0)

# ==========================================================
# KEY INSIGHTS
# ==========================================================
st.header("📌 Key Insights")

# Stock Metrics
total_items = len(merged)
total_inventory_stock = merged["Stock"].sum()
total_book_stock = merged["Book Stock"].sum()
total_phys_stock = merged["Phys Stock"].sum()
total_diff_stock = merged["Diff Stock"].sum()

st.subheader("🗃 Stock Summary")
st.write(f"Total items in inventory: {total_items}")
st.write(f"Total inventory stock: {total_inventory_stock}")
st.write(f"Total book stock: {total_book_stock}")
st.write(f"Total physical stock: {total_phys_stock}")
st.write(f"Total stock variance: {total_diff_stock}")

# Value Metrics
total_inventory_value = merged["Stock Value"].sum()
total_book_value = merged["Book Value"].sum()
total_phys_value = merged["Phys Value"].sum()
total_diff_value = merged["Diff Value"].sum()

st.subheader("💰 Value Summary")
st.write(f"Total inventory value: {total_inventory_value}")
st.write(f"Total book value: {total_book_value}")
st.write(f"Total physical value: {total_phys_value}")
st.write(f"Total variance value: {total_diff_value}")

# Variance Insights
zero_variance_count = merged[merged["Diff Stock"] == 0].shape[0]
missing_variance_count = merged[merged["Book Stock"] == 0].shape[0]

st.subheader("⚠️ Variance Insights")
st.write(f"Items with zero stock variance: {zero_variance_count}")
st.write(f"Items missing from stock variance file: {missing_variance_count}")

# High Variance Alerts (top 10)
st.subheader("🚨 Top 10 High Variance Items")
high_variance = merged.sort_values(by="Diff Value", ascending=False).head(10)
st.dataframe(high_variance[["Item Bar Code","Item Name","Diff Stock","Diff Value"]], use_container_width=True)

# ==========================================================
# SEPARATE TABLE: ITEMS IN INVENTORY BUT NOT IN VARIANCE
# ==========================================================
st.header("📋 Items in Inventory but Missing from Stock Variance")
missing_variance_items = merged[merged["Book Stock"] == 0].copy()
st.dataframe(missing_variance_items, use_container_width=True)

# ==========================================================
# DOWNLOAD MERGED RESULT
# ==========================================================
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventory_vs_Variance")
    return output.getvalue()

excel_data = to_excel(merged)
st.download_button(
    label="📥 Download Final Excel Report",
    data=excel_data,
    file_name="Final_Inventory_Variance_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
