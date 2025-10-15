import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ======================================================
# --- PAGE CONFIGURATION ---
# ======================================================
st.set_page_config(page_title="📊 Retail Insights Dashboard", layout="wide")

# ======================================================
# --- LOAD DATA (CACHED for SPEED) ---
# ======================================================
@st.cache_data
def load_data(file_path):
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()  # Clean spaces
    # Ensure numeric columns
    num_cols = ["Total Sales", "Stock Value", "Margin%", "Stock"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

# ======================================================
# --- FILE INPUT ---
# ======================================================
st.sidebar.header("📂 File Upload / Path")
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = load_data(uploaded_file)
else:
    file_path = "ItemSearchList.xlsx"
    if not os.path.exists(file_path):
        st.error("❌ File not found. Please upload or check the path.")
        st.stop()
    df = load_data(file_path)

# ======================================================
# --- SIDEBAR FILTERS ---
# ======================================================
st.sidebar.header("🔍 Filters")

# Category filter
categories = ["All"] + sorted(df["Category"].dropna().unique().tolist())
selected_category = st.sidebar.selectbox("Select Category", categories)

# Search inputs
search_item = st.sidebar.text_input("Search Item Name").strip().lower()
search_barcode = st.sidebar.text_input("Search Barcode").strip()

# Page navigation
page = st.sidebar.radio(
    "📂 Select Page",
    ["Dashboard", "GP Analysis", "Item Insights", "Zero Sales Stock"]
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
# --- DASHBOARD PAGE ---
# ======================================================
if page == "Dashboard":
    st.title("📊 Sales and Stock Dashboard")

    # Detect monthly columns dynamically
    monthly_cols = [
        col for col in df.columns
        if "," in col and any(m in col for m in
                              ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ]

    # Melt for monthly analysis
    sales_melted = filtered_df.melt(
        id_vars=["Item Name", "Category"],
        value_vars=monthly_cols,
        var_name="Month",
        value_name="Sales"
    )

    # Fix month order
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    sales_melted["Month"] = pd.Categorical(
        sales_melted["Month"],
        categories=[m for m in month_order if any(m in x for x in sales_melted["Month"])],
        ordered=True
    )
    sales_melted = sales_melted.sort_values("Month")

    # === Monthly Total Sales Chart ===
    monthly_sales = sales_melted.groupby("Month")["Sales"].sum().reset_index()
    fig1 = px.bar(
        monthly_sales,
        x="Month",
        y="Sales",
        title="📈 Monthly Total Sales",
        text_auto=".2s",
        color="Sales"
    )
    st.plotly_chart(fig1, use_container_width=True)

    # === Total Sales by Category ===
    cat_sales = filtered_df.groupby("Category")["Total Sales"].sum().reset_index()
    fig2 = px.bar(
        cat_sales,
        x="Category",
        y="Total Sales",
        title="🏷️ Total Sales by Category",
        text_auto=".2s",
        color="Category"
    )
    st.plotly_chart(fig2, use_container_width=True)

    # === KPI CARDS ===
    total_sales = filtered_df["Total Sales"].sum()
    total_stock_value = filtered_df["Stock Value"].sum()
    avg_margin = filtered_df["Margin%"].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Sales", f"{total_sales:,.0f}")
    col2.metric("📦 Total Stock Value", f"{total_stock_value:,.0f}")
    col3.metric("📈 Average Margin%", f"{avg_margin:.2f}%")

    # === Data Table ===
    st.dataframe(filtered_df, use_container_width=True, height=500)

# ======================================================
# --- GP ANALYSIS PAGE ---
# ======================================================
elif page == "GP Analysis":
    st.title("💹 Gross Profit Margin Analysis")

    gp_ranges = {
        "< 5%": df[df["Margin%"] < 5],
        "5% - 10%": df[(df["Margin%"] >= 5) & (df["Margin%"] < 10)],
        "10% - 20%": df[(df["Margin%"] >= 10) & (df["Margin%"] < 20)],
        "20% - 30%": df[(df["Margin%"] >= 20) & (df["Margin%"] < 30)],
        "> 30%": df[df["Margin%"] >= 30]
    }

    selected_range = st.selectbox("Select Margin Range", list(gp_ranges.keys()))
    selected_df = gp_ranges[selected_range]

    st.metric("🧾 Items in Range", len(selected_df))
    st.metric("💰 Total Sales in Range", f"{selected_df['Total Sales'].sum():,.0f}")

    fig3 = px.histogram(
        selected_df,
        x="Margin%",
        nbins=20,
        title=f"Distribution of GP% ({selected_range})"
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.dataframe(selected_df[["Item Name", "Category", "Margin%", "Total Sales"]],
                 use_container_width=True, height=500)

# ======================================================
# --- ITEM INSIGHTS PAGE ---
# ======================================================
elif page == "Item Insights":
    st.title("🔥 Item Wise Insights")

    # Top items by sales
    top_items = filtered_df.sort_values("Total Sales", ascending=False).head(20)

    fig4 = px.bar(
        top_items,
        x="Item Name",
        y="Total Sales",
        color="Category",
        title="🏆 Top 20 Items by Sales",
        text_auto=".2s"
    )
    fig4.update_layout(xaxis={'categoryorder': 'total descending'})
    st.plotly_chart(fig4, use_container_width=True)

    st.dataframe(top_items[["Item Bar Code", "Item Name", "Category", "Total Sales", "Margin%", "Stock"]],
                 use_container_width=True, height=500)

# ======================================================
# --- ZERO SALES STOCK PAGE ---
# ======================================================
elif page == "Zero Sales Stock":
    st.title("🚨 Zero Sales but with Stock Value")

    zero_sales_df = df[(df["Total Sales"] == 0) & (df["Stock Value"] > 0)]

    st.metric("📦 Total Items in Zero Sales", len(zero_sales_df))
    st.metric("💰 Total Stock Value", f"{zero_sales_df['Stock Value'].sum():,.0f}")

    fig5 = px.bar(
        zero_sales_df.head(20),
        x="Item Name",
        y="Stock Value",
        color="Category",
        title="Top 20 Items with Stock Value but Zero Sales",
        text_auto=".2s"
    )
    st.plotly_chart(fig5, use_container_width=True)

    st.dataframe(zero_sales_df[["Item Bar Code", "Item Name", "Category", "Stock Value", "Stock"]],
                 use_container_width=True, height=500)
