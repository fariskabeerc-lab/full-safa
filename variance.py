import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px # Added for generating standard dashboard charts

# --- Configuration & Utility Variables ---

# NOTE: You MUST update this list with the actual file names of your Excel reports.
# Ensure these files are in the same directory as your Streamlit app file.
EXCEL_FILES = ['Outlet A.xlsx', 'Outlet B.xlsx', 'Outlet C.xlsx'] 

# Standard headers confirmed to work for most files
STANDARD_COLUMNS = ['Item Code', 'Items', 'Total Sales']

# Flexible search terms for the two problematic files (expanded Item Code list)
SEARCH_TERMS = {
    'Item Code': ['item code', 'barcode', 'code', 'sku', 'product code', 'item no', 'item#'], 
    'Item Name': ['item', 'name', 'items', 'product'], # We rename 'Items' to 'Item Name' below
    'Total Sales': ['total sales', 'sales', 'quantity'] 
}

# Custom CSS for better UI and aesthetics
st.markdown("""
<style>
    /* Main container adjustments */
    .stApp {
        background-color: #f8f9fa; /* Light background */
    }
    .stDataFrame {
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-radius: 8px;
    }
    /* Metric styling */
    div[data-testid="stMetric"] > div[data-testid="stText"] {
        font-weight: 600;
        font-size: 1.1rem;
        color: #4a4e69;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0077b6; /* Blue primary color */
    }
</style>
""", unsafe_allow_html=True)


# --- Utility Function to Find the Correct Column Name ---
def find_column(df_columns, search_terms):
    """Finds the actual column name in the DataFrame based on a list of search terms."""
    df_columns_lower = {col.lower().strip(): col for col in df_columns}
    
    for term in search_terms:
        # Check for full match
        if term in df_columns_lower:
            return df_columns_lower[term]
        
        # Check for partial match (e.g., 'total sales' matches 'Total Sales (SAR)')
        for col_lower, original_col in df_columns_lower.items():
            if term in col_lower:
                return original_col
                
    return None

# --- Data Loading and Caching (Loads ONCE for speed!) ---
@st.cache_data
def load_data():
    """Reads all Excel files, combines them, and adds an 'Outlet' column."""
    all_data = []
    load_errors = []
    
    st.info(f"Attempting robust data load from {len(EXCEL_FILES)} files. Primary headers: {STANDARD_COLUMNS}...")
    
    for file in EXCEL_FILES:
        outlet_name = file.replace(".Xlsx", "").replace(".xlsx", "").strip() 
        df_loaded = None
        
        try:
            # Try loading the file, starting from the first sheet (default)
            df = pd.read_excel(file)
            
            # --- ATTEMPT 1: Use Standard Headers ---
            try:
                df_loaded = df[STANDARD_COLUMNS].copy()
                df_loaded = df_loaded.rename(columns={'Items': 'Item Name'})
            
            except KeyError:
                # --- ATTEMPT 2: Use Flexible Matching (if standard headers fail) ---
                column_map = {}
                for target_name, search_list in SEARCH_TERMS.items():
                    actual_name = find_column(df.columns, search_list)
                    if actual_name:
                        column_map[actual_name] = target_name
                    else:
                        raise KeyError(f"Could not find a match for '{target_name}' in the file headers.")
                
                df_loaded = df[column_map.keys()].copy()
                df_loaded = df_loaded.rename(columns=column_map)
                
                if 'Items' in df_loaded.columns: # Clean up the 'Items' column if found
                     df_loaded = df_loaded.rename(columns={'Items': 'Item Name'})
                
        except KeyError as e:
            load_errors.append(f"⚠️ Column error in **{outlet_name}**. {e}. This file will be skipped.")
            continue 
            
        except FileNotFoundError:
            load_errors.append(f"❌ File not found: **{file}**. Check file name and path. Skipping.")
            continue

        except Exception as e:
            load_errors.append(f"🔥 Generic Error reading **{file}**: {e}. This file will be skipped.")
            continue

        if df_loaded is not None:
            df_loaded['Outlet'] = outlet_name
            
            # Final data cleaning for the core columns
            df_loaded['Item Code'] = df_loaded['Item Code'].astype(str).fillna('').str.strip()
            df_loaded['Item Name'] = df_loaded['Item Name'].astype(str).fillna('').str.strip()
            df_loaded['Total Sales'] = pd.to_numeric(df_loaded['Total Sales'], errors='coerce').fillna(0)
            
            all_data.append(df_loaded)

    if load_errors:
        st.error("Some files failed to load due to errors:")
        for error in load_errors:
            st.markdown(error)

    if not all_data:
        st.error("❌ Fatal Error: No data could be loaded. Deployment halted.")
        st.stop() 
        
    combined_df = pd.concat(all_data, ignore_index=True)
    
    return combined_df

# --- Heatmap Generation ---
def render_sales_heatmap(df_filtered):
    """Generates a heatmap showing sales volume of top items across different outlets."""
    st.subheader("Sales Distribution Heatmap: Top Items by Outlet")
    st.markdown("Easily identify which outlets are the strongest performers for your top-selling products.")

    # 1. Identify Top Items (Top 15 for better readability in the map)
    top_item_names = df_filtered.groupby('Item Name')['Total Sales'].sum().nlargest(15).index

    # 2. Filter data for only those top items
    df_heatmap = df_filtered[df_filtered['Item Name'].isin(top_item_names)].copy()
    
    # 3. Aggregate sales by Outlet and Item Name
    df_pivot = df_heatmap.groupby(['Outlet', 'Item Name'])['Total Sales'].sum().reset_index()

    if not df_pivot.empty:
        # 4. Create the heatmap
        fig_hm = px.density_heatmap(
            df_pivot,
            x="Outlet",
            y="Item Name",
            z="Total Sales",
            histfunc="sum",
            title="Sales Volume by Item and Outlet (AED)",
            color_continuous_scale="Viridis", # High-contrast color scale
        )
        
        # Improve layout for cleaner look
        fig_hm.update_layout(
            xaxis_title="Outlet",
            yaxis_title="Item Name",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info("Not enough data to generate a sales heatmap for the current filter selection.")


# --- Key Insights / Standard Dashboard View ---
def render_key_insights(df_filtered):
    """Displays the key performance indicators and top performers for the currently filtered data."""
    
    st.header("Overall Performance Snapshot (Jun-Sep)", divider='blue')
    
    # 1. KPI Calculations (Based on available columns)
    total_sales = df_filtered['Total Sales'].sum()
    unique_items = df_filtered['Item Code'].nunique()
    total_outlets_reporting = df_filtered['Outlet'].nunique()
    
    # 2. Key Metric Cards
    col1, col2, col3 = st.columns(3)

    # Total Sales (Revenue) - requested
    with col1:
        st.metric(
            label="Total Sales (Revenue)",
            value=f"AED {total_sales:,.0f}",
        )

    # Unique Items (Replaced Stock Value) - standard KPI
    with col2:
        st.metric(
            label="Total Unique Items (SKUs)",
            value=f"{unique_items:,.0f}"
        )
        
    # Total Outlets - standard KPI
    with col3:
        st.metric(
            label="Outlets Reporting (Filtered)",
            value=f"{total_outlets_reporting}"
        )

    st.markdown("---")
    
    # 3. Top Sales/Revenue Items Chart (Bar Chart) - requested
    st.subheader("Top 10 Items: Total Revenue (Bar Chart)")
    
    # Calculate top items
    top_items = df_filtered.groupby('Item Name')['Total Sales'].sum().reset_index()
    top_items = top_items.sort_values(by='Total Sales', ascending=False).head(10)
    
    # Updated Bar Chart Styling
    fig = px.bar(
        top_items, 
        x='Total Sales', 
        y='Item Name', 
        orientation='h',
        title=None, # Remove internal title for cleaner look
        color_discrete_sequence=['#0077b6'], # Consistent primary blue color
        height=400
    ).update_layout(
        yaxis={'categoryorder':'total ascending'}, 
        xaxis_title="Total Revenue (AED)",
        yaxis_title="Item Name",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    
    # 4. Sales Heatmap
    render_sales_heatmap(df_filtered)
    
    st.markdown("---")


# --- Streamlit App Layout ---
def main():
    st.set_page_config(
        page_title="Outlet Item Sales Dashboard(Jun-Sep) 📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("Outlet Inventory and Sales Analysis Dashboard(Jun-Sep) 🛒")
    st.markdown("""
        Use this tool to find an item's sales performance across all outlets. This dashboard helps managers 
        identify **high-performing outlets** for stock transfer of overstocked items.
        """)
    
    # LOAD DATA (Will run only once due to @st.cache_data)
    df_combined = load_data()

    # --- Sidebar Filters ---
    st.sidebar.header("🎯 Dashboard Filters")
    
    all_outlets = sorted(df_combined['Outlet'].unique())
    
    # Category/Outlet Selection filter (as requested)
    selected_outlets = st.sidebar.multiselect(
        "Filter by Outlet (Category)",
        options=all_outlets,
        default=all_outlets, # Default to selecting all, like the 'All' option
        key='outlet_filter'
    )
    
    st.sidebar.markdown("---")
    
    # Apply Outlet filter to the main dataset
    if selected_outlets:
        df_filtered_by_outlet = df_combined[df_combined['Outlet'].isin(selected_outlets)]
    else:
        # Handle case where nothing is selected (displaying nothing or a message)
        df_filtered_by_outlet = pd.DataFrame() 
        st.warning("Please select at least one Outlet to view the dashboard and search results.")
        # Render the dashboard with no data if no outlets are selected
        render_key_insights(df_filtered_by_outlet) 
        return


    # --- Search Functionality (Drill Down) ---
    st.sidebar.header("🔍 Item Search Drill Down")
    
    search_mode = st.sidebar.radio(
        "Select Search Type:",
        ("Search by Item Name (Partial Match)", "Search by Barcode (Exact Match)"),
        key='search_mode'
    )

    search_term = st.sidebar.text_input(
        f"Enter the search term for **{search_mode.split('(')[0].strip()}**:",
        placeholder="e.g., Al Marai or 628100100001",
        key='search_term'
    ).strip()

    filtered_df = pd.DataFrame()
    
    if search_term:
        
        # --- Search Logic (searches within the already outlet-filtered data) ---
        if "Name" in search_mode:
            # Item Name Search (Partial Match)
            filtered_df = df_filtered_by_outlet[
                df_filtered_by_outlet['Item Name'].str.contains(search_term, case=False, na=False)
            ].copy()
            st.subheader(f"Results for Item Name containing: **{search_term}**")
            
        elif "Barcode" in search_mode:
            # Barcode Search (Exact Match)
            filtered_df = df_filtered_by_outlet[
                df_filtered_by_outlet['Item Code'].str.strip() == search_term
            ].copy()
            st.subheader(f"Results for Barcode: **{search_term}**")


        # --- Display Search Results ---
        if not filtered_df.empty:
            
            # Display item name only if multiple items were found (Name search)
            item_names = filtered_df['Item Name'].unique()
            if len(item_names) > 1 and "Name" in search_mode:
                st.info(f"Found {len(item_names)} distinct item names matching '{search_term}'.")

            
            # Group by Item Code and Name across all outlets
            grouped_df = filtered_df.groupby(['Item Code', 'Item Name']).agg(
                Total_Overall_Sales=('Total Sales', 'sum'),
                Outlets_Selling=('Outlet', 'count'),
                Sales_Distribution=('Outlet', lambda x: ', '.join(x.unique()))
            ).reset_index().sort_values(by='Total_Overall_Sales', ascending=False)
            
            st.markdown("### Item Sales Summary Across All Selected Outlets")
            st.dataframe(
                grouped_df.rename(columns={
                    'Total_Overall_Sales': 'Total Sales (Selected Outlets)',
                    'Outlets_Selling': 'Num Outlets Selling',
                    'Sales_Distribution': 'Outlets List'
                }),
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("---")
            
            # --- Individual Outlet Sales Table ---
            st.markdown("### Individual Outlet Performance (Sorted by Sales)")
            display_cols = ['Outlet', 'Item Code', 'Item Name', 'Total Sales']
            
            st.dataframe(
                filtered_df[display_cols].sort_values(by='Total Sales', ascending=False),
                use_container_width=True,
                hide_index=True
            )
            
            st.info("The table above shows the specific sales figure for each item in each outlet.")
            
        else:
            st.warning("No items found matching your search criteria in the **selected outlets**. Please try a different code or name, or adjust the **Outlet Filter**.")
    else:
        # --- Standard Dashboard View (KPIs) ---
        # Only show the main dashboard if no search term is entered
        render_key_insights(df_filtered_by_outlet)
        st.info("👈 Use the search box for a specific item, or use the **Outlet Filter** above to adjust the dashboard view.")

# --- Run the application ---
if __name__ == "__main__":
    main()
