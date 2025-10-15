import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- Configuration for Layout and Mobile/Laptop Responsiveness ---
st.set_page_config(
    page_title="Advanced Retail Sales Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI and responsiveness (especially on mobile)
st.markdown("""
<style>
    /* Main container styling for responsiveness and padding */
    .main-content {
        padding: 1rem 1rem 4rem 1rem;
    }
    
    /* Key Metric Cards Styling */
    .metric-card {
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        text-align: center;
        margin-bottom: 15px;
        transition: transform 0.2s;
        border-left: 5px solid #4F46E5; /* Accent color */
        background-color: #ffffff;
    }
    .metric-card:hover {
        transform: translateY(-3px);
    }
    .metric-title {
        font-size: 0.9rem;
        color: #6B7280;
        margin-bottom: 5px;
        font-weight: 500;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1F2937;
    }

    /* Streamlit-specific overrides for mobile view */
    @media (max-width: 600px) {
        .metric-value {
            font-size: 1.4rem;
        }
        .metric-title {
            font-size: 0.8rem;
        }
        .stMultiSelect, .stSelectbox {
            margin-bottom: 0.5rem;
        }
    }
    
    /* Adjust Streamlit wide container for better use of space */
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Loading and Pre-processing Logic ---
@st.cache_data
def load_and_preprocess_data(file_path):
    """Loads, cleans, and transforms the data from the provided path."""
    
    # st.subheader(f"Data Source: `{file_path}`", divider='blue') # Removed for cleaner UI
    # st.info(f"Attempting to read file from path: `{file_path}`...") # Removed for cleaner UI
    
    with st.spinner(f"Loading and preprocessing data from **`{file_path}`**..."):
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
        except FileNotFoundError:
            st.error(f"File not found: **`{file_path}`**. Please ensure the file exists at this exact path.")
            st.stop()
        except Exception as e:
            st.error(f"An error occurred while reading the Excel file: {e}")
            st.stop()


    # 1. More Robust Column Cleaning and Standardization (Handles 'Margin%' -> 'Margin_Percent')
    df.columns = df.columns.str.strip().str.replace(' ', '_').str.replace('%', '_Percent', regex=False).str.replace('[^A-Za-z0-9_]', '', regex=True)
    
    # Identify sales columns (e.g., 'Sep_2025', 'Aug_2025')
    monthly_cols = [col for col in df.columns if any(month in col for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])]

    # --- Data Cleaning and Type Conversion ---
    numeric_cols = ['Cost', 'Selling', 'Stock'] 
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    for col in monthly_cols:
         df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)


    # Recalculate/Verify Key Metrics
    # Note: We use Stock for Profit calculation since Pack_Qty is missing.
    df['Margin_Recalc'] = ((df['Selling'] - df['Cost']) / df['Selling']).clip(lower=0) * 100
    df['Profit_Recalc'] = (df['Selling'] - df['Cost']) * df['Stock'].fillna(0) 
    df['Stock_Value_Recalc'] = df['Cost'] * df['Stock']
    df['Total_Sales_Recalc'] = df[monthly_cols].sum(axis=1)

    # Use the recalculated columns as primary analysis points (also ensures 'Profit' column exists)
    df['Margin_Percent'] = df.get('Margin_Percent', df['Margin_Recalc']) # Use existing Margin% if it exists, otherwise use recalc
    df['Profit'] = df['Profit_Recalc']
    df['Stock_Value'] = df['Stock_Value_Recalc'] 
    df['Total_Sales'] = df['Total_Sales_Recalc'] 

    # --- Dynamic ID Vars for Melting (Fixes the KeyError) ---
    base_id_vars = [
        'Item_Bar_Code', 'Item_Name', 'Category', 'Cost', 'Selling', 
        'Stock', 'Margin_Percent', 'Profit', 'Stock_Value', 'Total_Sales'
    ]
    
    # Check for optional categorical columns and add them only if they exist
    optional_id_vars = ['Brand', 'Group']
    final_id_vars = base_id_vars + [col for col in optional_id_vars if col in df.columns]


    # --- Melt the monthly sales columns into a long format for time-series analysis ---
    df_melted = df.melt(
        id_vars=final_id_vars,
        value_vars=monthly_cols,
        var_name='Sales_Month',
        value_name='Monthly_Sales_Value'
    )
    
    # Clean up month names and convert to proper datetime objects for sorting
    df_melted['Sales_Month'] = df_melted['Sales_Month'].str.replace('_', ', ', regex=False)
    try:
        df_melted['Date_Sort'] = pd.to_datetime(df_melted['Sales_Month'], format='%b, %Y')
    except:
        st.warning("Could not automatically parse all month columns. Sorting might be alphabetical.")
        df_melted['Date_Sort'] = df_melted['Sales_Month'] 

    return df, df_melted

# --- Key Insights Rendering Function ---
def render_key_insights(df_filtered):
    """Calculates and displays key performance indicators at the top of the dashboard using custom cards."""
    
    # Calculate Metrics from the filtered data
    total_sales = df_filtered['Monthly_Sales_Value'].sum()
    
    # Profit and Stock Value are item-level attributes (same value across all month rows for one item).
    # Use groupby to select the unique value for each item before summing.
    total_profit = df_filtered.groupby('Item_Bar_Code')['Profit'].first().sum() 
    current_stock_value = df_filtered.groupby('Item_Bar_Code')['Stock_Value'].first().sum() 
    avg_margin = df_filtered.groupby('Item_Bar_Code')['Margin_Percent'].first().mean()
    
    # Format numbers for display (Using AED)
    sales_str = f"AED{total_sales:,.0f}" if total_sales > 1000 else f"AED{total_sales:,.2f}"
    profit_str = f"AED{total_profit:,.0f}" if total_profit > 1000 else f"AED{total_profit:,.2f}"
    stock_str = f"AED{current_stock_value:,.0f}" if current_stock_value > 1000 else f"AED{current_stock_value:,.2f}"
    margin_str = f"{avg_margin:.1f}%"
    
    st.subheader("Key Performance Insights", divider='rainbow')

    # Use columns for responsive card layout
    col1, col2, col3, col4 = st.columns(4)

    # Use f-strings with triple quotes here is necessary to apply the custom CSS card style
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">TOTAL SALES VALUE (Filtered)</div>
            <div class="metric-value">{sales_str}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">ESTIMATED PROFIT (Total Potential)</div>
            <div class="metric-value">{profit_str}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">CURRENT STOCK VALUE (Cost)</div>
            <div class="metric-value">{stock_str}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">AVERAGE MARGIN %</div>
            <div class="metric-value">{margin_str}</div>
        </div>
        """, unsafe_allow_html=True)

# --- Main Dashboard Page Function ---
def main_dashboard(df_raw, df_melted):
    st.title("Comprehensive Sales Performance Overview")
    
    # --- Sidebar Filtering and Search ---
    st.sidebar.header("Global Filters & Search")

    # 1. Item Search (Barcode or Name)
    search_term = st.sidebar.text_input("Search Item (Barcode or Name)", "").strip()

    # 2. Main Filters (Category, Brand)
    st.sidebar.subheader("Filter Data")
    all_categories = df_raw['Category'].unique()
    selected_categories = st.sidebar.multiselect("Select Category(s)", all_categories, default=all_categories)
    
    # Conditional Brand Filter
    selected_brands = []
    if 'Brand' in df_raw.columns:
        all_brands = df_raw['Brand'].unique()
        selected_brands = st.sidebar.multiselect("Select Brand(s)", all_brands, default=all_brands)
    
    # --- Filtering Logic ---
    if search_term:
        # Filter based on search term (logic remains the same)
        search_df = df_raw[
            (df_raw['Item_Bar_Code'].astype(str).str.contains(search_term, case=False, na=False)) |
            (df_raw['Item_Name'].astype(str).str.contains(search_term, case=False, na=False))
        ]
        
        # ... (rest of the item search display logic) ...
        # If search yields results, show Item Details
        if not search_df.empty:
            st.header(f"🔍 Item Details for '{search_term}'")
            # Select the first matching item for detailed display
            item_data = search_df.iloc[0]
            
            with st.expander(f"Detailed Metrics for: {item_data['Item_Name']}", expanded=True):
                
                # Format variables once (Using AED)
                stock_val_str = f"AED{item_data['Stock_Value']:,.2f}"
                cost_str = f"AED{item_data['Cost']:,.2f}"
                selling_str = f"AED{item_data['Selling']:,.2f}"
                margin_str = f"{item_data['Margin_Percent']:,.1f}%"

                colA, colB, colC = st.columns(3)
                colA.metric("Barcode", item_data['Item_Bar_Code'])
                colB.metric("Category", item_data['Category'])
                colC.metric("Current Stock", f"{item_data['Stock']:,.0f} units")
                
                if 'Brand' in df_raw.columns:
                    st.metric("Brand", item_data['Brand'])
                
                st.markdown("---")
                
                colD, colE, colF, colG = st.columns(4)
                colD.metric("Stock Value (Cost)", stock_val_str)
                colE.metric("Unit Cost", cost_str)
                colF.metric("Unit Selling Price", selling_str)
                colG.metric("Profit Margin %", margin_str, delta_color="normal")
                
                st.subheader("Month-wise Sales Value for this Item")
                # Extract monthly sales for the specific item
                item_monthly_sales = df_melted[df_melted['Item_Bar_Code'] == item_data['Item_Bar_Code']] \
                    .sort_values(by='Date_Sort')

                fig_item_sales = px.line(
                    item_monthly_sales, 
                    x='Sales_Month', 
                    y='Monthly_Sales_Value', 
                    title=f'Monthly Sales for {item_data["Item_Name"]}',
                    markers=True
                ).update_layout(xaxis_title="Month", yaxis_title="Sales Value (AED)")
                st.plotly_chart(fig_item_sales, use_container_width=True)
            
            # Don't show global dashboard charts if a specific item is being searched
            return 
        else:
            st.warning(f"No item found matching '{search_term}'. Showing results based on filters.")
            
    # Apply category and brand filters to melted data (if not searching)
    df_filtered = df_melted[
        (df_melted['Category'].isin(selected_categories))
    ]
    
    # Apply brand filter only if the column exists and selections were made
    if 'Brand' in df_raw.columns and selected_brands:
        df_filtered = df_filtered[df_filtered['Brand'].isin(selected_brands)]


    if df_filtered.empty:
        st.info("No data matches the selected filters.")
        return

    # --- 1. Key Insights at Top ---
    render_key_insights(df_filtered)

    # --- 2. Main Visualizations ---
    
    col_chart_1, col_chart_2 = st.columns(2)

    with col_chart_1:
        # A. Category-wise Sales (Total over filtered period)
        st.subheader("Total Sales Value by Category")
        category_sales = df_filtered.groupby('Category')['Monthly_Sales_Value'].sum().reset_index()
        category_sales = category_sales.sort_values('Monthly_Sales_Value', ascending=False)
        
        fig_cat_sales = px.bar(
            category_sales.head(10), # Top 10 categories
            x='Monthly_Sales_Value',
            y='Category',
            orientation='h',
            title="Top 10 Categories by Sales",
            color_discrete_sequence=px.colors.qualitative.Pastel
        ).update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Sales Value (AED)")
        st.plotly_chart(fig_cat_sales, use_container_width=True)

    with col_chart_2:
        # B. Month-wise Sales (Overall over filtered period)
        st.subheader("Overall Monthly Sales Trend")
        monthly_sales = df_filtered.groupby('Date_Sort').agg(
            {'Monthly_Sales_Value': 'sum', 'Sales_Month': 'first'}
        ).sort_values(by='Date_Sort').reset_index()

        fig_month_sales = px.line(
            monthly_sales,
            x='Sales_Month',
            y='Monthly_Sales_Value',
            title="Monthly Sales Trend",
            markers=True,
            line_shape='spline',
            color_discrete_sequence=['#4F46E5']
        ).update_layout(xaxis_title="Month", yaxis_title="Sales Value (AED)")
        st.plotly_chart(fig_month_sales, use_container_width=True)
        
    st.markdown("---")
    
    # C. Which month a category did the most sales (Category vs Month analysis)
    st.subheader("Category Sales Performance Across Months")
    
    # Calculate total monthly sales per category
    category_month_sales = df_filtered.groupby(['Category', 'Sales_Month', 'Date_Sort'])['Monthly_Sales_Value'].sum().reset_index()
    category_month_sales = category_month_sales.sort_values(by='Date_Sort')

    # Find the best month for each category
    best_month_per_category = category_month_sales.loc[category_month_sales.groupby('Category')['Monthly_Sales_Value'].idxmax()]
    
    # Create an interactive heatmap to show performance visually
    fig_heatmap = px.density_heatmap(
        category_month_sales, 
        x='Sales_Month', 
        y='Category', 
        z='Monthly_Sales_Value', 
        height=600,
        title="Sales Heatmap: Category Performance by Month (Hover for Value)",
        color_continuous_scale="Plasma"
    ).update_xaxes(tickangle=45)
    st.plotly_chart(fig_heatmap, use_container_width=True)

    with st.expander("Best Month Summary Table", expanded=False):
        st.dataframe(
            best_month_per_category[['Category', 'Sales_Month', 'Monthly_Sales_Value']]
            .rename(columns={'Sales_Month': 'Peak Sales Month', 'Monthly_Sales_Value': 'Peak Sales Value (AED)'})
            .sort_values('Peak Sales Value (AED)', ascending=False),
            hide_index=True,
            use_container_width=True
        )


# --- Margin Analysis Page Function ---
def margin_analysis_page(df_raw):
    st.title("Pricing Strategy and Margin Health Check")
    
    st.info("""
        This page allows you to segment your inventory based on calculated profit margin percentages. 
        It's crucial for identifying low-margin items that might need repricing, promotion, or discontinuation, 
        and high-margin items to capitalize on.
    """)
    
    # Define margin groups
    margin_groups = {
        "🔴 Critical (< 5%)": (0, 5),
        "🟠 Low (5% to 10%)": (5, 10),
        "🟡 Medium (10% to 20%)": (10, 20),
        "🟢 Good (20% to 30%)": (20, 30),
        "🔵 Excellent (30%+ )": (30, 1000)
    }

    # Create the filter list in the sidebar for segmentation
    st.sidebar.header("Margin Segmentation Filter")
    selected_groups = st.sidebar.multiselect(
        "Select Margin Groups to Analyze",
        list(margin_groups.keys()),
        default=["🔴 Critical (< 5%)", "🟡 Medium (10% to 20%)", "🔵 Excellent (30%+ )"]
    )
    
    # Apply filtering logic
    df_margin = df_raw.copy()
    df_margin['Margin_Group'] = 'Other' # Default group
    
    if not selected_groups:
        st.warning("Please select at least one Margin Group to display data.")
        return

    # Create the combined filter condition
    filter_condition = pd.Series([False] * len(df_margin))
    
    for group_name in selected_groups:
        min_val, max_val = margin_groups[group_name]
        
        # Apply group name and update filter condition
        if group_name == "🔵 Excellent (30%+ )":
            group_filter = (df_margin['Margin_Percent'] >= min_val)
        else:
            group_filter = (df_margin['Margin_Percent'] >= min_val) & (df_margin['Margin_Percent'] < max_val)

        df_margin.loc[group_filter, 'Margin_Group'] = group_name
        filter_condition = filter_condition | group_filter

    df_filtered_margin = df_margin[filter_condition]


    # --- Analysis & Visualization ---
    st.subheader("Inventory Breakdown by Margin Group")
    
    col_chart_1, col_chart_2 = st.columns([1, 2])
    
    with col_chart_1:
        # Pie chart showing count of items in each group
        item_count = df_filtered_margin.groupby('Margin_Group').size().reset_index(name='Item_Count')
        fig_pie = px.pie(
            item_count, 
            names='Margin_Group', 
            values='Item_Count', 
            title='Count of Items per Margin Group',
            hole=.3,
            color_discrete_sequence=['#EF4444', '#F59E0B', '#FACC15', '#10B981', '#3B82F6']
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart_2:
        # Bar chart showing total stock value by margin group
        stock_value_by_group = df_filtered_margin.groupby('Margin_Group')['Stock_Value'].sum().reset_index()
        fig_bar = px.bar(
            stock_value_by_group.sort_values('Stock_Value', ascending=False),
            x='Margin_Group',
            y='Stock_Value',
            title='Total Cost Value of Stock in Each Margin Group',
            labels={'Stock_Value': 'Total Stock Value (AED)', 'Margin_Group': 'Margin Group'},
            color='Margin_Group',
            color_discrete_sequence=['#EF4444', '#F59E0B', '#FACC15', '#10B981', '#3B82F6']
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    
    st.subheader("Detailed Item List")
    
    # Prepare data for display
    display_cols = [
        'Margin_Group', 'Item_Name', 'Category', 'Stock', 'Stock_Value', 
        'Cost', 'Selling', 'Margin_Percent', 'Total_Sales'
    ]
    
    # Conditionally add Brand if it exists in the data frame
    if 'Brand' in df_raw.columns:
        display_cols.insert(display_cols.index('Category') + 1, 'Brand')

    
    df_display = df_filtered_margin[display_cols].rename(columns={
        'Margin_Percent': 'Margin %',
        'Stock_Value': 'Stock Value (AED)', 
        'Total_Sales': 'Total Sales (AED)' 
    })

    # Convert currency columns for clean display
    currency_cols = ['Stock Value (AED)', 'Cost', 'Selling', 'Total Sales (AED)']
    for col in currency_cols:
        df_display[col] = df_display[col].apply(lambda x: f"AED{x:,.2f}")
        
    df_display['Margin %'] = df_display['Margin %'].apply(lambda x: f"{x:,.1f}%")

    # Display the filtered dataframe
    st.dataframe(df_display, hide_index=True, use_container_width=True)
    
    st.markdown("---")
    st.info("""
        **Actionable Insights:**
        * **🔴 Critical (< 5%):** Review these items immediately. Can we increase the selling price? Negotiate a better cost? Or should we phase them out?
        * **🔵 Excellent (30%+):** These are your cash cows. Focus marketing efforts here and ensure stock levels are adequate to meet demand.
    """)


# --- Main Application Logic ---
def app():
    st.title("Retail Sales Dashboard")

    # Direct file path assignment (like in old projects)
    file_path = "ItemSearchList.xlsx" 
    
    st.sidebar.info(f"File path set directly in code: **{file_path}**")

    # Load and preprocess data. The function now handles errors/stopping if file is missing.
    df_raw, df_melted = load_and_preprocess_data(file_path)
    
    # If the function didn't stop, the data frames are ready
    
    # --- Page Selection in Sidebar ---
    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "Select Dashboard View",
        ["📊 Sales Overview", "📉 Margin Analysis"],
        index=0 # Default to Sales Overview
    )

    # Dispatch to the selected page function
    if page == "📊 Sales Overview":
        main_dashboard(df_raw, df_melted)
    elif page == "📉 Margin Analysis":
        margin_analysis_page(df_raw)

# Run the application
if __name__ == '__main__':
    app()
