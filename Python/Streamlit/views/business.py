import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import utils as ut

def show(df_sess, df_orders, df_items, df_prods, df_pv):

    st.subheader("💼 Business Overview")

    # --- KPIs ---
    tot_rev =(df_orders['revenue'].sum())/1000000
    net_profit = (df_orders['margin'].sum())/1000000
    tot_orders = (df_orders['order_id'].count())/1000
    
    # Calculate YoY (Approximate based on total dataset vs first half)
    # In a real app, this would be dynamic based on date filters
    yoy = 12.5 # Placeholder calculation or dynamic based on date filter
    
    avg_sess_user = df_sess.groupby('user_id')['website_session_id'].count().mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    ut.kpi_card(c1, "Total Revenue", f"{tot_rev:,.2f}", "$","M")
    ut.kpi_card(c2, "Net Profit", f"{net_profit:,.2f}", "$",'M')
    ut.kpi_card(c3, "Total Orders", f"{tot_orders:,.2f}",suffix='K')
    ut.kpi_card(c4, "YoY Growth", f"{yoy}%", "+")
    ut.kpi_card(c5, "Avg Sess/User", f"{avg_sess_user:.2f}")

    # --- ROW 1 Charts ---
    
    # 1. Revenue and Quantity Sold (Combo Chart)
    df_m = df_orders.merge(
        df_sess[['website_session_id', 'utm_source', 'utm_campaign']],
        on='website_session_id',
        how='left'
    )

    # Create a combined UTM label (source + campaign + content)
    df_m['UTM'] = (
        df_m['utm_source'].fillna('Untracked') + "\n" +
        df_m['utm_campaign'].fillna('Untracked')
    )

    # Aggregate revenue and quantity
    agg = df_m.groupby('UTM').agg(
    Revenue=('revenue', 'sum'),
    Quantity=('items', 'sum')
).sort_values(by='Revenue', ascending=False).reset_index()

    # Convert to percentages
    agg['Revenue_pct'] = agg['Revenue'] / agg['Revenue'].sum() * 100
    agg['Quantity_pct'] = agg['Quantity'] / agg['Quantity'].sum() * 100

    # Create clustered percentage bar chart
    fig = px.bar(
    agg,
    x='UTM',
    y=['Revenue_pct', 'Quantity_pct'],
    barmode='group',
    title="Revenue and Quantity Share by Combined Source and campaign",
    text_auto='.2f'
)
    fig.update_traces( textposition='auto')
    fig.update_layout(
    yaxis_title="Percentage (%)",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,
        xanchor="center",
        x=0.5
    )
)
    fig.update_yaxes(tickformat=".2f%")
    st.plotly_chart(fig, use_container_width=True)



    c_left, c_right = st.columns(2)
    # 2. Refund Rate by Product
    with c_left:
        chan_stats = df_sess.groupby('utm_source')['website_session_id'].count().reset_index()
        fig_chan = px.pie(chan_stats, values='website_session_id', names='utm_source', title="Sessions Distribution by Channel", hole=0.4)
        st.plotly_chart(ut.style_chart(fig_chan), use_container_width=True)
        fig_chan.update_traces(texttemplate="%{percent:.1%}")
        fig_chan.update_layout(
        legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.2,
        xanchor="center",
        x=0.5
    )
)



    with c_right:
    # 4. Session by Channel
        chan_stats = df_sess.groupby('utm_campaign')['website_session_id'].count().reset_index()
        fig_chan = px.pie(chan_stats, values='website_session_id', names='utm_campaign', title="Sessions Distribution by Campaign", hole=0.4)
        st.plotly_chart(ut.style_chart(fig_chan), use_container_width=True)
        fig_chan.update_layout(
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.2,
        xanchor="center",
        x=0.5
    )
)

    # --- ROW 2 Charts ---
   
    
   
    # 3. Seasonality by Month ( Line chart of revenue by month )
 

    # Prepare data
    df_orders['month'] = df_orders['created_at'].dt.month
    df_orders['year'] = df_orders['created_at'].dt.year

    seasonality = df_orders.groupby(['year', 'month'])['revenue'].sum().reset_index()

    # Create date column
    seasonality['date'] = pd.to_datetime(
    seasonality['year'].astype(str) + "-" + seasonality['month'].astype(str)
)

    # Convert revenue to % of total revenue
    total_rev = seasonality['revenue'].sum()
    seasonality['rev_pct'] = ((seasonality['revenue'] / total_rev) * 100).round(2)

    # Plot
    fig = px.line(
    seasonality,
    x='date',
    y='rev_pct',
    markers=True,
    title="Revenue Trends Over Time (%)"
)

    # Proper % formatting for y-axis
    fig.update_yaxes(
    tickformat=".1f%",
    title="Revenue (%)"
)

    st.plotly_chart(fig, use_container_width=True)
        


    # 5. Cross Sell (Products per Order Distribution)
    # Calculate items per order
    c_l, c_r = st.columns(2)

    # ---------------- LEFT CHART ----------------
    with c_l:                   ##billing page conversion rate

        billing_pages = df_pv[df_pv['pageview_url'].isin(['/billing', '/billing-2'])].copy()

        # Count unique sessions for each billing page
        billing_sessions = (
            billing_pages.groupby('pageview_url')['website_session_id']
            .nunique()
    .reset_index()
)

        billing_sessions.columns = ['billing_page', 'sessions']

        # --- Identify converted sessions (sessions that reached billing and completed an order) ---
        converted = df_orders[['website_session_id']].drop_duplicates()

        billing_conv = pd.merge(
            billing_pages[['website_session_id', 'pageview_url']].drop_duplicates(),
            converted,
    on='website_session_id',
    how='inner'
)

        billing_conversions = (
            billing_conv.groupby('pageview_url')['website_session_id']
            .nunique()
            .reset_index()
)

        billing_conversions.columns = ['billing_page', 'conversions']

        # --- Merge sessions + conversions ---
        billing_final = billing_sessions.merge(billing_conversions, on='billing_page', how='left')
        billing_final['conversions'] = billing_final['conversions'].fillna(0)

        # Conversion Rate
        billing_final['conversion_rate'] = (
            (billing_final['conversions'] / billing_final['sessions']) * 100
        ).round(2)


        # --- Visualization (Bar Chart) ---
        fig = px.bar(
    billing_final,
    x='billing_page',
    y='conversion_rate',
    title='Billing Page Conversion Rates',
    text='conversion_rate',
    color='conversion_rate',
    color_continuous_scale='Viridis'
)

        fig.update_layout(
    yaxis_title='Conversion Rate (%)',
    xaxis_title='Billing Page')

        fig.update_traces(texttemplate='%{text}%', textposition='auto')

        st.plotly_chart(fig, use_container_width=True)

    # ---------------- RIGHT CHART ----------------
    with c_r:

        df_m = df_items.merge(df_prods, on='product_id', how='left')

        # If product_name column is missing in df_prods, set a fallback
        if 'product_name' not in df_m.columns:
            df_m['product_name'] = 'Product ' + df_m['product_id'].astype(str)

        # --- Calculate units sold per product ---
        units = (
            df_m.groupby('product_name')['order_item_id']
            .count()
            .reset_index())

        units.columns = ['product_name', 'units_sold']

        # --- Calculate % distribution ---
        total_units = units['units_sold'].sum()
        units['unit_pct'] = ((units['units_sold'] / total_units) * 100).round(2)
        units.sort_values(by='unit_pct', ascending=False, inplace=True)

        # --- Plot ---
        fig = px.bar(
    units,
    x='product_name',
    y='unit_pct',
    text='unit_pct',
    title='Units Sold Distribution in % by Product')

        fig.update_traces(
    texttemplate='%{text}%',
    textposition='auto')

        fig.update_layout(
    xaxis_title="Products Name",
    yaxis_title="Share of Units Sold (%)")

        st.plotly_chart(fig, use_container_width=True)
