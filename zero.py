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
inventory_path = "zero sales(1).xlsx"        # Replace with your local file path
variance_path = "SAO Stock Comparison On 15-Sep-2025 1(1)(1).Xlsx"    # Replace with your local file path

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
# DISPLAY RESULTS
# ==========================================================
st.success("✅ Inventory comparison complete")

# Summary stats
total_items = len(df_inventory)
found_in_variance = merged[merged["Book Stock"] != 0].shape[0]
not_in_variance = total_items - found_in_variance

st.write(f"**Total items in inventory:** {total_items}")
st.write(f"**Items found in stock variance:** {found_in_variance}")
st.write(f"**Items missing from stock variance:** {not_in_variance}")

# Show full table
st.dataframe(merged, use_container_width=True)

# ==========================================================
# DOWNLOAD MERGED RESULT
# ==========================================================
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventory_vs_Variance")
    processed_data = output.getvalue()
    return processed_data

excel_data = to_excel(merged)
st.download_button(
    label="📥 Download Final Excel Report",
    data=excel_data,
    file_name="Final_Inventory_Variance_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
