import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ======================================================
# --- PAGE CONFIGURATION ---
# ======================================================
st.set_page_config(page_title="📊 Retail Insights Dashboard", layout="wide")

# ======================================================
# --- LOAD DATA ---
# ======================================================
@st.cache_data
def load_data(file_path):
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()
    # Ensure numeric columns
    num_cols = ["Total Sales", "Stock Value", "Margin%", "Stock"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

# ======================================================
# --- FILE PATH ---
# ======================================================
file_path = "ItemSearchList.xlsx"
if not os.path.exists(file_path):
    st.error("❌ File not found. Please check the path.")
    st.stop()
df = load_data(file_path)

# ======================================================
# --- SIDEBAR FILTERS ---
# ======================================================
st.sidebar.header("🔍 Filters")

categories = ["All"] + sorted(df["Category"].dropna().unique().tolist())
selected_category = st.sidebar.selectbox("Select Category", categories)

search_item = st.sidebar.text_input("Search Item Name").strip().lower()
search_barcode = st.sidebar.text_input("Search Barcode").strip()

page = st.sidebar.radio(
    "📂 Select Page",
    ["GP Analysis", "Item Insights", "Zero Sales Stock"]
)

# ======================================================
# --- FILTERING LOGIC ---
# ======================================================
filtered_df = df.copy()

if selected_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]

if search_item:
    filtered_df = filtered_df[filtered_df["Item Name"].str.lower().str.contains(search_item)]

if search_barcode:
    filtered_df = filtered_df[filtered_df["Item Bar Code"].astype(str).str.contains(search_barcode)]

if filtered_df.empty:
    st.warning("🚫 No items found for your filters/search.")
    st.stop()

# ======================================================
# --- GP ANALYSIS PAGE ---
# ======================================================
if page == "GP Analysis":
    st.title("💹 Gross Profit Margin Analysis")

    gp_ranges = {
        "< 5%": filtered_df[filtered_df["Margin%"] < 5],
        "5% - 10%": filtered_df[(filtered_df["Margin%"] >= 5) & (filtered_df["Margin%"] < 10)],
        "10% - 20%": filtered_df[(filtered_df["Margin%"] >= 10) & (filtered_df["Margin%"] < 20)],
        "20% - 30%": filtered_df[(filtered_df["Margin%"] >= 20) & (filtered_df["Margin%"] < 30)],
        "> 30%": filtered_df[filtered_df["Margin%"] >= 30]
    }

    selected_range = st.selectbox("Select Margin Range", list(gp_ranges.keys()))
    selected_df = gp_ranges[selected_range]

    st.metric("🧾 Items in Range", len(selected_df))
    st.metric("💰 Total Sales in Range", f"{selected_df['Total Sales'].sum():,.0f}")

    fig = px.histogram(
        selected_df,
        x="Margin%",
        nbins=20,
        title=f"Distribution of GP% ({selected_range})",
        text_auto=True
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(selected_df[["Item Name", "Category", "Margin%", "Total Sales"]],
                 use_container_width=True, height=500)

# ======================================================
# --- ITEM INSIGHTS PAGE ---
# ======================================================
elif page == "Item Insights":
    st.title("🔥 Item Wise Insights")

    # Sort all filtered items by Total Sales
    sorted_df = filtered_df.sort_values("Total Sales", ascending=False)

    fig = px.bar(
        sorted_df.head(20),
        x="Item Name",
        y="Total Sales",
        color="Category",
        title="🏆 Top 20 Items by Sales",
        text_auto=".2s"
    )
    fig.update_layout(xaxis={'categoryorder': 'total descending'})
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(sorted_df[["Item Bar Code", "Item Name", "Category", "Total Sales", "Margin%", "Stock"]],
                 use_container_width=True, height=500)

# ======================================================
# --- ZERO SALES STOCK PAGE ---
# ======================================================
elif page == "Zero Sales Stock":
    st.title("🚨 Zero Sales but with Stock Value")

    zero_sales_df = filtered_df[(filtered_df["Total Sales"] == 0) & (filtered_df["Stock Value"] > 0)]

    st.metric("📦 Total Items in Zero Sales", len(zero_sales_df))
    st.metric("💰 Total Stock Value", f"{zero_sales_df['Stock Value'].sum():,.0f}")

    fig = px.bar(
        zero_sales_df.head(20),
        x="Item Name",
        y="Stock Value",
        color="Category",
        title="Top 20 Items with Stock Value but Zero Sales",
        text_auto=".2s"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(zero_sales_df[["Item Bar Code", "Item Name", "Category", "Stock Value", "Stock"]],
                 use_container_width=True, height=500)
