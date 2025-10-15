import streamlit as st
import pandas as pd
import plotly.express as px
import os # Import os for checking file existence

# ======================================================
# --- PAGE CONFIGURATION ---
# ======================================================
st.set_page_config(page_title="📊 Retail Insights Dashboard", layout="wide")

# ======================================================
# --- LOAD DATA (CACHED for SPEED) ---
# ======================================================
@st.cache_data
def load_data(file_path):
    # Check if file exists before trying to read it
    if not os.path.exists(file_path):
        st.error(f"File not found: {file_path}. Please ensure the Excel file is in the correct location.")
        # Create an empty DataFrame with expected columns to prevent application crash
        expected_cols = ["Category", "Item Name", "Item Bar Code", "Total Sales", "Stock Value", "Margin%", "Stock",
                         "Jan,Sales", "Feb,Sales", "Mar,Sales", "Apr,Sales", "May,Sales", "Jun,Sales",
                         "Jul,Sales", "Aug,Sales", "Sep,Sales", "Oct,Sales", "Nov,Sales", "Dec,Sales"]
        return pd.DataFrame(columns=expected_cols)
    
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()  # Clean spaces
        # Ensure key columns exist or fill with defaults
        for col in ["Category", "Item Name", "Item Bar Code", "Total Sales", "Stock Value", "Margin%", "Stock"]:
            if col not in df.columns:
                df[col] = 0 if col in ["Total Sales", "Stock Value", "Margin%", "Stock"] else ""
        return df
    except Exception as e:
        st.error(f"Error reading the file: {e}")
        return pd.DataFrame()


# ======================================================
# --- FILE PATH (Change to your Excel file path) ---
# ======================================================
file_path = "ItemSearchList.xlsx"  # ⬅️ Replace this path
df = load_data(file_path)

# Handle case where DataFrame is empty due to file error
if df.empty:
    st.stop() # Stop the app if data loading failed

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

# ======================================================
# --- PAGE NAVIGATION ---
# ======================================================
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
    # Ensure "Item Name" is treated as string and handles potential NaNs
    filtered_df = filtered_df[filtered_df["Item Name"].astype(str).str.lower().str.contains(search_item)]

if search_barcode:
    # Ensure "Item Bar Code" is treated as string
    filtered_df = filtered_df[filtered_df["Item Bar Code"].astype(str).str.contains(search_barcode)]

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
    
    if monthly_cols:
        # Melt for monthly analysis
        sales_melted = filtered_df.melt(
            id_vars=["Item Name", "Category"],
            value_vars=monthly_cols,
            var_name="Month",
            value_name="Sales"
        )

        # === Monthly Total Sales Chart ===
        monthly_sales = sales_melted.groupby("Month")["Sales"].sum().reset_index()
        # Order months correctly for display
        month_order = [m.split(',')[0] for m in monthly_cols] # Extract month names
        
        # Ensure 'Month' column is categorical with the correct order
        monthly_sales['Month'] = pd.Categorical(
            monthly_sales['Month'], 
            categories=monthly_cols, 
            ordered=True
        )
        monthly_sales = monthly_sales.sort_values('Month')
        
        fig1 = px.bar(
            monthly_sales,
            x="Month",
            y="Sales",
            title="📈 Monthly Total Sales",
            text_auto=".2s",
            color="Sales"
        )
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No monthly sales columns detected (e.g., 'Jan,Sales'). Monthly chart is skipped.")

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
    # Calculate weighted average margin (Total GP / Total Sales * 100)
    # Assuming 'Total GP' is not available, we use the simple mean as in the original code, 
    # but check for an empty filtered_df to prevent division errors.
    avg_margin = filtered_df["Margin%"].mean() if not filtered_df.empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Sales", f"{total_sales:,.2f}")
    col2.metric("📦 Total Stock Value", f"{total_stock_value:,.2f}")
    col3.metric("📈 Average Margin%", f"{avg_margin:.2f}%")

    # === Data Table ===
    st.dataframe(filtered_df, use_container_width=True, height=500)

# ======================================================
# --- GP ANALYSIS PAGE (FIXED) ---
# ======================================================
elif page == "GP Analysis":
    st.title("💹 Gross Profit Margin Analysis")

    # CORRECTED: Use filtered_df to respect sidebar filters
    gp_ranges = {
        "< 5%": filtered_df[filtered_df["Margin%"] < 5],
        "5% - 10%": filtered_df[(filtered_df["Margin%"] >= 5) & (filtered_df["Margin%"] < 10)],
        "10% - 20%": filtered_df[(filtered_df["Margin%"] >= 10) & (filtered_df["Margin%"] < 20)],
        "20% - 30%": filtered_df[(filtered_df["Margin%"] >= 20) & (filtered_df["Margin%"] < 30)],
        "> 30%": filtered_df[filtered_df["Margin%"] >= 30]
    }

    selected_range = st.selectbox("Select Margin Range", list(gp_ranges.keys()))
    selected_df = gp_ranges[selected_range]
    
    if selected_df.empty:
        st.info(f"No items found in the '{selected_range}' margin range with the current filters.")
        st.stop()

    col_gp1, col_gp2 = st.columns(2)
    col_gp1.metric("🧾 Items in Range", len(selected_df))
    col_gp2.metric("💰 Total Sales in Range", f"{selected_df['Total Sales'].sum():,.2f}")

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
    
    if filtered_df.empty:
        st.info("No items found with the current filters.")
        st.stop()

    # Top items by sales
    top_items = (
        filtered_df.sort_values("Total Sales", ascending=False)
        .head(20)
    )
    
    if top_items.empty or top_items["Total Sales"].sum() == 0:
        st.info("No sales found for the filtered items.")
    else:
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

        # Show data
        st.dataframe(top_items[["Item Bar Code", "Item Name", "Category", "Total Sales", "Margin%", "Stock"]],
                    use_container_width=True, height=500)

# ======================================================
# --- ZERO SALES STOCK PAGE (FIXED) ---
# ======================================================
elif page == "Zero Sales Stock":
    st.title("🚨 Zero Sales but with Stock Value")

    # CORRECTED: Use filtered_df to respect sidebar filters
    # Find items with Total Sales == 0 AND Stock Value > 0 within the filtered set
    zero_sales_df = filtered_df[(filtered_df["Total Sales"] == 0) & (filtered_df["Stock Value"] > 0)]
    
    if zero_sales_df.empty:
        st.balloons()
        st.success("🎉 Excellent! No items with stock have recorded zero sales for the filtered criteria.")
        st.stop()

    col_zs1, col_zs2 = st.columns(2)
    col_zs1.metric("📦 Total Items in Zero Sales", len(zero_sales_df))
    col_zs2.metric("💰 Total Stock Value", f"{zero_sales_df['Stock Value'].sum():,.2f}")

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
