


import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pandas.tseries.offsets import MonthEnd
import os  # <-- Import the OS library

# --- Page Setup ---
st.set_page_config(page_title="E-Commerce Performance Dashboard", page_icon="🐻", layout="wide")

# --- FIXED: Make paths relative to the script itself ---
# This gets the absolute path to the folder containing dashboard.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Helper function to build the full path
def _build_path(file_name):
    return os.path.join(SCRIPT_DIR, file_name)

# --- Helper function for loading files ---
def _try_read(paths):
    # 'paths' is now a list of full, absolute paths
    for p in paths:
        try:
            if p.endswith('.csv'):
                return pd.read_csv(p)
            elif p.endswith('.xlsx'):
                return pd.read_excel(p)
        except FileNotFoundError:
            continue
# If we get here, no file was found.
# We strip the long directory path for a cleaner error message
        clean_paths = [os.path.basename(p) for p in paths]
        st.error(f"Error: Could not find any of these files in your script directory: {clean_paths}")
        st.stop() # <-- This is the crucial part that prevents the 'NoneType' error

@st.cache_data
def load_all_data():
    """
    Loads all CSVs OR EXCELs, parses dates, and performs ESSENTIAL cleaning.
    """
    ### FIXED: Using the exact lowercase .csv filenames from your screenshot ###
    df_sessions = _try_read([_build_path('website_sessions.csv')])
    df_pageviews = _try_read([_build_path('website_pageviews.csv')])
    df_orders = _try_read([_build_path('orders.csv')])
    df_order_items = _try_read([_build_path('order_items.csv')])
    df_products = _try_read([_build_path('products.csv')])
    df_order_item_refunds = _try_read([_build_path('order_item_refunds.csv')])

    # --- 1. Parse Dates ---
    for df in [df_sessions, df_pageviews, df_orders, df_order_items, df_products, df_order_item_refunds]:
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')

    # --- 2. Clean Data (from our analysis) ---

    # Normalize referrer
    if 'http_referrer' not in df_sessions.columns and 'http_referer' in df_sessions.columns:
        df_sessions['http_referrer'] = df_sessions['http_referer']
    if 'http_referrer' in df_sessions.columns:
        df_sessions['http_referrer'] = df_sessions['http_referrer'].fillna('direct/unknown')
    else:
        df_sessions['http_referrer'] = 'direct/unknown' # Ensure col exists

    # Smart UTM Cleaning
    if 'utm_source' not in df_sessions.columns:
        df_sessions['utm_source'] = pd.NA
    df_sessions['utm_source'] = df_sessions['utm_source'].fillna('Untracked')
    
    missing_utm = df_sessions['utm_source'] == 'Untracked'
    referer_norm = df_sessions['http_referrer'].astype(str).str.strip().str.lower()
    
    mapping = {
        'https://www.gsearch.com': 'gsearch',
        'https://www.bsearch.com': 'bsearch',
        'https://www.socialbook.com': 'socialbook',
    }

    for url, source in mapping.items():
        mask = (referer_norm == url) & missing_utm
        df_sessions.loc[mask, 'utm_source'] = source
        
    for c in ['utm_campaign', 'utm_content']:
        if c not in df_sessions.columns:
            df_sessions[c] = 'unknown'
        else:
            df_sessions[c] = df_sessions[c].fillna('unknown')

    # Drop 'orphaned' orders
    if 'website_session_id' in df_orders.columns:
        df_orders = df_orders.dropna(subset=['website_session_id']).copy()
    
    # Ensure critical columns exist
    if 'price_usd' not in df_order_items.columns: df_order_items['price_usd'] = 0.0
    if 'cogs_usd' not in df_order_items.columns: df_order_items['cogs_usd'] = 0.0
    if 'order_item_id' not in df_order_items.columns: df_order_items['order_item_id'] = pd.NA

    # Calculate margin
    df_order_items['price_usd'] = pd.to_numeric(df_order_items['price_usd'], errors='coerce').fillna(0.0)
    df_order_items['cogs_usd'] = pd.to_numeric(df_order_items['cogs_usd'], errors='coerce').fillna(0.0)
    df_order_items['margin'] = df_order_items['price_usd'] - df_order_items['cogs_usd']

    # Flag refunds
    refunded_ids = df_order_item_refunds['order_item_id'].unique() if 'order_item_id' in df_order_item_refunds.columns else []
    df_order_items['is_refunded'] = df_order_items['order_item_id'].isin(refunded_ids)

    # Clean products
    if 'product_name' not in df_products.columns and 'product_id' in df_products.columns:
        df_products['product_name'] = 'Product ' + df_products['product_id'].astype(str)
    if 'product_name' not in df_products.columns:
        df_products['product_name'] = 'Unknown Product'
        
    # --- 3. Pre-calculate Metrics ---
    if 'order_id' in df_order_items.columns:
        order_agg = df_order_items.groupby('order_id', dropna=False).agg(
            total_revenue=('price_usd', 'sum'),
            total_margin=('margin', 'sum')
        ).reset_index()
    else:
        order_agg = pd.DataFrame(columns=['order_id', 'total_revenue', 'total_margin'])

    if 'order_id' in df_orders.columns:
        df_full_orders = df_orders.merge(order_agg, on='order_id', how='left')
    else:
        df_full_orders = df_orders.copy()
        df_full_orders['total_revenue'] = 0.0
        df_full_orders['total_margin'] = 0.0
        
    df_full_orders['total_revenue'] = df_full_orders['total_revenue'].fillna(0.0)
    df_full_orders['total_margin'] = df_full_orders['total_margin'].fillna(0.0)

    return df_sessions, df_pageviews, df_orders, df_order_items, df_products, df_order_item_refunds, df_full_orders
@st.cache_data
def get_landing_page_stats(_pageviews_df, _sessions_df, _orders_df):
    """
    Calculates CVR and Bounce Rate for landing pages for the filtered data.
    """
    # Use copies to avoid caching issues
    pageviews_df = _pageviews_df.copy()
    sessions_df = _sessions_df.copy()
    orders_df = _orders_df.copy()
    
    # Defensive check for empty dataframes
    if pageviews_df.empty or 'website_session_id' not in pageviews_df.columns or 'created_at' not in pageviews_df.columns:
        return pd.DataFrame(columns=['pageview_url','total_sessions','bounced_sessions','converted_sessions','bounce_rate','cvr']).set_index('pageview_url')

    # Find first pageview
    first_pageviews = pageviews_df.sort_values(by=['website_session_id', 'created_at']) \
                                  .groupby('website_session_id') \
                                  .first()
    
    # Count pageviews per session
    session_page_counts = pageviews_df.groupby('website_session_id').size()
    bounced_session_ids = session_page_counts[session_page_counts == 1].index
    
    # Get converted sessions
    converted_session_ids = orders_df['website_session_id'].unique() if 'website_session_id' in orders_df.columns else []
    
    # Map to landing page
    first_pageviews['is_bounced'] = first_pageviews.index.isin(bounced_session_ids)
    first_pageviews['is_converted'] = first_pageviews.index.isin(converted_session_ids)
    
    # Aggregate stats
    if 'pageview_url' not in first_pageviews.columns:
         return pd.DataFrame(columns=['pageview_url','total_sessions','bounced_sessions','converted_sessions','bounce_rate','cvr']).set_index('pageview_url')
         
    landing_stats = first_pageviews.groupby('pageview_url').agg(
        total_sessions=('is_bounced', 'count'),
        bounced_sessions=('is_bounced', 'sum'),
        converted_sessions=('is_converted', 'sum')
    )
    
    landing_stats['bounce_rate'] = landing_stats['bounced_sessions'] / landing_stats['total_sessions']
    landing_stats['cvr'] = landing_stats['converted_sessions'] / landing_stats['total_sessions']
    
    return landing_stats.sort_values(by='total_sessions', ascending=False)

# --- Load Data ---
data_load_state = st.text("Loading data...")
dfs = load_all_data()
df_sessions, df_pageviews, df_orders, df_order_items, df_products, df_order_item_refunds, df_full_orders = dfs
data_load_state.text("Loading data... Done!")

# --- Sidebar Filters ---
st.sidebar.header("Dashboard Filters")
if df_sessions['created_at'].isna().all():
    min_date = pd.Timestamp.today().normalize()
    max_date = min_date
else:
    min_date = df_sessions['created_at'].min().date()
    max_date = df_sessions['created_at'].max().date()

dates = pd.date_range(min_date, max_date, freq='D')
if len(dates) == 0:
    dates = pd.DatetimeIndex([min_date])

start_sel, end_sel = st.sidebar.select_slider(
    'Select Date Range:',
    options=list(dates),
    value=(dates[0], dates[-1]),
    format_func=lambda date: date.strftime('%Y-%m-%d')
)
st.sidebar.markdown(f"**Selected Period:** `{pd.to_datetime(start_sel).date()}` to `{pd.to_datetime(end_sel).date()}`")

# --- Filter DataFrames based on selection ---
start_datetime = pd.to_datetime(start_sel)
end_datetime = pd.to_datetime(end_sel) + pd.Timedelta(days=1) # Make it inclusive of the end day

df_sessions_filt = df_sessions[(df_sessions['created_at'] >= start_datetime) & (df_sessions['created_at'] < end_datetime)].copy()
df_orders_filt = df_orders[(df_orders['created_at'] >= start_datetime) & (df_orders['created_at'] < end_datetime)].copy()
df_pageviews_filt = df_pageviews[df_pageviews['website_session_id'].isin(df_sessions_filt['website_session_id'])].copy() if 'website_session_id' in df_pageviews.columns else pd.DataFrame()
df_full_orders_filt = df_full_orders[df_full_orders['website_session_id'].isin(df_sessions_filt['website_session_id'])].copy() if 'website_session_id' in df_full_orders.columns else pd.DataFrame()
df_order_items_filt = df_order_items[(df_order_items['created_at'] >= start_datetime) & (df_order_items['created_at'] < end_datetime)].copy()

# --- Main Dashboard ---
st.title("🐻 E-Commerce Performance Dashboard")
st.markdown(f"Analyzing data from **{pd.to_datetime(start_sel).date()}** to **{pd.to_datetime(end_sel).date()}**")

# --- Tabs ---
tab_website, tab_channel, tab_traffic, tab_user, tab_product = st.tabs([
    "🌐 Website", "📣 Channel", "📈 Traffic", "👥 User", "🧸 Product"
])

# --- Tab 1: Website ---
with tab_website:
    st.header("Website & Funnel Performance")
    
    # Calculate KPIs
    total_sessions = df_sessions_filt['website_session_id'].nunique() if not df_sessions_filt.empty else 0
    total_orders = df_orders_filt['order_id'].nunique() if not df_orders_filt.empty else 0
    total_revenue = df_full_orders_filt['total_revenue'].sum() if not df_full_orders_filt.empty else 0.0
    cvr = (total_orders / total_sessions) if total_sessions > 0 else 0.0
    rev_per_session = (total_revenue / total_sessions) if total_sessions > 0 else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sessions", f"{total_sessions:,}")
    col2.metric("Total Orders", f"{total_orders:,}")
    col3.metric("Conversion Rate", f"{cvr:.2%}")
    col4.metric("Revenue per Session", f"${rev_per_session:.2f}")

    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    lp_stats = get_landing_page_stats(df_pageviews_filt, df_sessions_filt, df_orders_filt)
    
    with col1:
        st.subheader("Landing Pages")
        if not lp_stats.empty:
            lp_plot_data = lp_stats.head(10).reset_index()
            fig_top_pages = px.bar(
                lp_plot_data,
                y='pageview_url',
                x='total_sessions',
                orientation='h',
                title='Top 10 Landing Pages by Session',
                labels={'pageview_url': 'Landing Page', 'total_sessions': 'Total Sessions'},
                text='total_sessions'
            )
            fig_top_pages.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
            fig_top_pages.update_traces(textposition='outside')
            st.plotly_chart(fig_top_pages, use_container_width=True)
        else:
            st.info("No landing page data for this period.")

    with col2:
        st.subheader("Landing Page Performance")
        st.dataframe(
            lp_stats[['total_sessions', 'cvr', 'bounce_rate']].head(10),
            column_config={
                "total_sessions": st.column_config.NumberColumn(format="%d"),
                "cvr": st.column_config.ProgressColumn(
                    "CVR", format="%.2f%%",
                    min_value=0, max_value=lp_stats['cvr'].max() if not lp_stats.empty else 1
                ),
                "bounce_rate": st.column_config.ProgressColumn(
                    "Bounce Rate", format="%.2f%%",
                    min_value=0, max_value=lp_stats['bounce_rate'].max() if not lp_stats.empty else 1
                ),
            },
            use_container_width=True
        )

# --- Tab 2: Channel ---
with tab_channel:
    st.header("Channel & Marketing Performance")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Traffic Source Distribution")
        source_dist = df_sessions_filt['utm_source'].value_counts(normalize=True)
        
        fig_pie = px.pie(
            source_dist,
            values=source_dist.values,
            names=source_dist.index,
            title="Session Distribution by Channel (utm_source)",
            hole=0.3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("New vs. Repeat Channel Patterns")
        if 'is_repeat_session' in df_sessions_filt.columns:
            df_sessions_filt['session_type'] = df_sessions_filt['is_repeat_session'].map({0: 'New', 1: 'Repeat'})
            channel_dist = df_sessions_filt.groupby('session_type')['utm_source'] \
                                         .value_counts(normalize=True) \
                                         .to_frame('percentage') \
                                         .reset_index()
            
            fig_channel_bar = px.bar(
                channel_dist,
                x='utm_source',
                y='percentage',
                color='session_type',
                barmode='group',
                title='Channel Usage: New vs. Repeat Sessions',
                labels={'utm_source': 'Channel', 'percentage': 'Percentage of Sessions'},
                text_auto='.1%'
            )
            st.plotly_chart(fig_channel_bar, use_container_width=True)
        else:
            st.info("Column 'is_repeat_session' not found.")

# --- Tab 3: Traffic ---
with tab_traffic:
    st.header("Traffic & Sales Trends")
    
    # Monthly Trends
    if not df_sessions_filt.empty and 'created_at' in df_sessions_filt.columns:
        df_sessions_filt = df_sessions_filt.copy()
        df_sessions_filt.loc[:, 'month'] = df_sessions_filt['created_at'].dt.to_period('M').astype(str)
        sessions_monthly = df_sessions_filt.groupby('month')['website_session_id'].nunique().rename('Sessions')
    else:
        sessions_monthly = pd.Series(dtype=int, name='Sessions')
        
    if not df_orders_filt.empty and 'created_at' in df_orders_filt.columns:
        df_orders_filt['month'] = df_orders_filt['created_at'].dt.to_period('M').astype(str)
        orders_monthly = df_orders_filt.groupby('month')['order_id'].nunique().rename('Orders')
    else:
        orders_monthly = pd.Series(dtype=int, name='Orders')

    df_trends = pd.concat([sessions_monthly, orders_monthly], axis=1).fillna(0).reset_index()
    
    fig_tr = go.Figure()
    fig_tr.add_trace(go.Scatter(x=df_trends['month'], y=df_trends['Sessions'], mode='lines+markers', name='Sessions'))
    fig_tr.add_trace(go.Scatter(x=df_trends['month'], y=df_trends['Orders'], mode='lines+markers', name='Orders', yaxis='y2'))
    fig_tr.update_layout(
        yaxis2=dict(overlaying='y', side='right'), 
        title='Monthly Trend: Sessions and Orders',
        legend=dict(x=0.1, y=1.1, orientation='h')
    )
    st.plotly_chart(fig_tr, use_container_width=True)
    
    st.subheader("Website Traffic Heatmap (by Day & Hour)")
    if not df_sessions_filt.empty:
        df_sessions_filt['hour'] = df_sessions_filt['created_at'].dt.hour
        df_sessions_filt['day_of_week'] = df_sessions_filt['created_at'].dt.day_name()
        
        heatmap_data = df_sessions_filt.groupby(['day_of_week', 'hour']).size().unstack().fillna(0)
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_data = heatmap_data.reindex(days_order)
        
        fig_heatmap = px.imshow(
            heatmap_data,
            aspect="auto",
            color_continuous_scale='Viridis',
            title='Session Volume by Day and Hour',
            labels=dict(x="Hour of Day", y="Day of Week", color="Sessions")
        )
        fig_heatmap.update_xaxes(nticks=24)
        st.plotly_chart(fig_heatmap, use_container_width=True)
    else:
        st.info("No session data to build heatmap.")

# --- Tab 4: User ---
with tab_user:
    st.header("User Behavior (New vs. Repeat)")
    
    merged = df_sessions_filt.merge(
        df_full_orders_filt[['website_session_id','total_revenue']], 
        on='website_session_id', 
        how='left'
    )
    
    if 'is_repeat_session' in merged.columns:
        merged['session_type'] = merged['is_repeat_session'].map({0:'New Session', 1:'Repeat Session'})
    else:
        merged['session_type'] = 'Unknown'
        
    merged['total_revenue'] = merged['total_revenue'].fillna(0)
    merged['is_converted'] = merged['website_session_id'].isin(df_orders_filt['website_session_id'])
    
    user_perf = merged.groupby('session_type').agg(
        total_sessions=('website_session_id','nunique'),
        total_conversions=('is_converted','sum'),
        total_revenue=('total_revenue','sum')
    )
    
    if not user_perf.empty and 'total_sessions' in user_perf.columns and 'total_conversions' in user_perf.columns:
        # Check for division by zero
        non_zero_sessions = user_perf['total_sessions'] > 0
        user_perf.loc[non_zero_sessions, 'cvr'] = user_perf.loc[non_zero_sessions, 'total_conversions'] / user_perf.loc[non_zero_sessions, 'total_sessions']
        user_perf.loc[non_zero_sessions, 'rev_per_session'] = user_perf.loc[non_zero_sessions, 'total_revenue'] / user_perf.loc[non_zero_sessions, 'total_sessions']
        # Fill 0 for cases with 0 sessions
        user_perf.fillna(0, inplace=True)
    else:
        user_perf['cvr'] = 0.0
        user_perf['rev_per_session'] = 0.0
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Conversion Rate")
        fig_user_cvr = px.bar(
            user_perf.reset_index(),
            x='session_type', y='cvr',
            color='session_type', text_auto='.2%',
            labels={'session_type': 'Session Type', 'cvr': 'CVR'}
        )
        fig_user_cvr.update_layout(yaxis_tickformat='.1%')
        st.plotly_chart(fig_user_cvr, use_container_width=True)

    with c2:
        st.subheader("Revenue per Session")
        fig_user_rev = px.bar(
            user_perf.reset_index(),
            x='session_type', y='rev_per_session',
            color='session_type', text_auto='.2f',
            labels={'session_type': 'Session Type', 'rev_per_session': 'Revenue per Session'}
        )
        fig_user_rev.update_layout(yaxis_tickformat='$.2f')
        st.plotly_chart(fig_user_rev, use_container_width=True)
    
    st.subheader("Raw Data")
    st.dataframe(user_perf, use_container_width=True)

# --- Tab 5: Product ---
with tab_product:
    st.header("Product Performance")
    
    df_items_with_names = df_order_items_filt.merge(
        df_products[['product_id','product_name']], 
        on='product_id', 
        how='left'
    ) if not df_order_items_filt.empty else pd.DataFrame(columns=list(df_order_items.columns) + ['product_name'])
    
    # Handle products that might be in order_items but not in products table
    if 'product_name' not in df_items_with_names.columns:
        df_items_with_names['product_name'] = 'Unknown Product'
    df_items_with_names['product_name'] = df_items_with_names['product_name'].fillna('Unknown Product')

    if not df_items_with_names.empty:
        prod_perf = df_items_with_names.groupby('product_name').agg(
            items_sold=('order_item_id','count'),
            total_revenue=('price_usd','sum'),
            total_margin=('margin','sum'),
            total_refunded=('is_refunded','sum')
        )
        prod_perf['refund_rate'] = (prod_perf['total_refunded'] / prod_perf['items_sold']).fillna(0)
        
        st.subheader("Product Performance Metrics")
        st.dataframe(
            prod_perf.sort_values('items_sold',ascending=False), 
            use_container_width=True,
            column_config={
                "total_revenue": st.column_config.NumberColumn(format="$%.2f"),
                "total_margin": st.column_config.NumberColumn(format="$%.2f"),
                "refund_rate": st.column_config.NumberColumn(format="%.2f%%", min_value=0, max_value=1)
            }
        )
        
        st.subheader("Monthly Product Refund Rate")
        df_items_with_names['month'] = df_items_with_names['created_at'].dt.to_period('M').astype(str)
        df_refund_trend = df_items_with_names.groupby(['month', 'product_name']).agg(
            items_sold=('order_item_id', 'count'),
            total_refunded=('is_refunded', 'sum')
        ).reset_index()
        
        df_refund_trend['refund_rate'] = (df_refund_trend['total_refunded'] / df_refund_trend['items_sold']).fillna(0.0)
        
        fig_refund_line = px.line(
            df_refund_trend,
            x='month',
            y='refund_rate',
            color='product_name',
            markers=True,
            title='Monthly Refund Rate by Product'
        )
        fig_refund_line.update_layout(yaxis_title='Refund Rate', yaxis_tickformat='.1%')
        st.plotly_chart(fig_refund_line, use_container_width=True)
    else:
        st.info("No product sales in the selected period.")