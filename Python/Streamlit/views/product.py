import streamlit as st
import pandas as pd
import plotly.express as px
import utils as ut
from itertools import combinations
from collections import Counter

def show(df_oi, df_p,df_pv,df_o,df_s):
    st.subheader("🧸 Product Dashboard")

    # --- CRITICAL FIX: Handle Duplicate Column Names ---
    # Both df_oi and df_p have a 'created_at' column.
    # We use suffixes=('', '_product') to keep the sales date as 'created_at'
    # and rename the product launch date to 'created_at_product'.
    df_m = df_oi.merge(
        df_p, 
        on='product_id', 
        how='left', 
        suffixes=('', '_product')
    )

    # Fallback for product name
    if 'product_name' not in df_m.columns:
        df_m['product_name'] = 'Prod ' + df_m['product_id'].astype(str)
    
    ##top product sold
    prod_rev = (df_m.groupby('product_name')['price_usd'].sum().reset_index())


    top_product = prod_rev.sort_values(by='price_usd', ascending=False).iloc[0]
    top_prod_name = top_product['product_name']



# KPI card


    # --- 1. KPIs ---
    total_sold = df_m['order_item_id'].count()
    total_rev = df_m['price_usd'].sum()
    avg_price = df_m['price_usd'].mean()
    total_refunds = df_m['is_refunded'].sum()
    refund_rate = total_refunds / total_sold if total_sold > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    ut.kpi_card(c1, "Total Units Sold", f"{total_sold/1000:,.2f}K")
    ut.kpi_card(c2, "Top Product by Revenue",top_prod_name)
    ut.kpi_card(c3, "Avg. Order Item Price", f"{avg_price:.2f}", "$")
    ut.kpi_card(c4, "Total Item Refunds", f"{total_refunds/1000:,.2f}K")
    ut.kpi_card(c5, "Refund Rate", f"{refund_rate:.2%}")

    # --- 2. Charts ---
    c_left, c_right = st.columns(2)

    with c_left:
        prod_rev = (df_m.groupby('product_name')['price_usd'].sum().reset_index())
        prod_rev['revenue_pct'] = (prod_rev['price_usd'] / prod_rev['price_usd'].sum() * 100).round(2)
        prod_rev.sort_values(by='revenue_pct', ascending=False, inplace=True)

        fig_sales = px.bar(
            prod_rev,
            x='product_name',
            y='revenue_pct',
            title="Revenue Distribution by Product (%)",
            text='revenue_pct',
            labels={'revenue_pct': 'Revenue (%)', 'product_name': 'Product'},
            color='revenue_pct',
            color_continuous_scale='Viridis')
    

        fig_sales.update_traces(texttemplate='%{text}%', textposition='auto')
        fig_sales.update_layout(yaxis_tickformat='.2f')

        st.plotly_chart(ut.style_chart(fig_sales), use_container_width=True)

    with c_right:
        # Refund Rate by Product
        prod_ref = df_m.groupby('product_name').agg(
            Sold=('order_item_id', 'count'),
            Refunded=('is_refunded', 'sum')
        ).reset_index()
        prod_ref['Rate'] = prod_ref['Refunded'] / prod_ref['Sold']
        prod_ref.sort_values(by='Rate', ascending=False, inplace=True)
        
        fig_ref = px.bar(prod_ref, x='product_name', y='Rate', title="Refund Rate by Product", 
                         text_auto='.1%', color='Rate', color_continuous_scale='Redor')
        st.plotly_chart(ut.style_chart(fig_ref), use_container_width=True)




####monthly sales trend####

    df_m['month'] = df_m['created_at'].dt.to_period('M').astype(str)
    trend = (df_m.groupby(['month','product_name'])['price_usd'].sum().reset_index())
    trend['sales_in_thousands'] = (trend['price_usd'].round(2)/1000).round(2)

    fig_trend = px.line(
    trend,
    x='month',
    y='sales_in_thousands',
    color='product_name',
    title="Monthly Sales Trend by Product",
    markers=True)
    fig_trend.update_layout(legend=dict(orientation='h', x=0, y=-0.3))

    st.plotly_chart(ut.style_chart(fig_trend), use_container_width=True)



    # Row 2

    c_left, c_right = st.columns(2)
    with c_left:
    # Cross Sell (Items per Order)
        ppo = df_oi.groupby('order_id')['order_item_id'].count().value_counts().sort_index().reset_index()
        ppo.columns = ['Items in Cart', 'Order Count']

    # Convert to % of total orders
        total_orders = ppo['Order Count'].sum()
        ppo['Order %'] = (ppo['Order Count'] / total_orders) * 100

    # Plot
        fig_cross = px.bar(
        ppo,
        x='Items in Cart',
        y='Order %',
        title="Items in Cart Distribution by Orders (Percentage)",
        text_auto='.2f'
    )

        fig_cross.update_traces(marker_color='green', textposition='auto')

        fig_cross.update_layout(
        yaxis_title="Percentage (%)"
    )

        st.plotly_chart(ut.style_chart(fig_cross), use_container_width=True)


    with c_right:

        prod_pages = [
            '/the-original-mr-fuzzy',
            '/the-forever-love-bear',
            '/the-birthday-sugar-panda',
            '/the-hudson-river-mini-bear'
        ]

# Filter pageviews for only these product pages
        pv_prod = df_pv[df_pv['pageview_url'].isin(prod_pages)]

# Unique sessions visiting each product page
        page_sessions = (pv_prod.groupby('pageview_url')['website_session_id']
                      .nunique()
                      .reset_index(name='sessions'))

# Unique converted sessions
        order_sessions = df_o['website_session_id'].unique()
        pv_prod['is_converted'] = pv_prod['website_session_id'].isin(order_sessions).astype(int)

# Count conversions per product page
        page_conversions = (pv_prod.groupby('pageview_url')['is_converted']
                        .sum()
                        .reset_index(name='orders'))

# Merge sessions + conversions + CVR
        cvr_df = page_sessions.merge(page_conversions, on='pageview_url', how='left')
        cvr_df['cvr'] = (cvr_df['orders'] / cvr_df['sessions'] * 100).round(2)
        cvr_df.sort_values(by='cvr', ascending=False, inplace=True)

# Gradient color column chart
        fig = px.bar(
        cvr_df,
        x='pageview_url',
        y='cvr',
        text='cvr',
        color='cvr',                         # gradient
        color_continuous_scale='Viridis',    # choose any: Viridis, Plasma, Magma
        title="Conversion Rate by Product Page (%)",
        labels={'pageview_url': 'Product Page', 'cvr': 'CVR (%)'}
)

        fig.update_traces(texttemplate='%{text}%', textposition='auto')
        fig.update_layout(coloraxis_showscale=False)   # remove side color bar

        st.plotly_chart(ut.style_chart(fig), use_container_width=True)



##cross selling##
    # Step 1: Prepare Data
    orders_data=df_o.copy()
    orders_data['created_at']=pd.to_datetime(orders_data['created_at'])
    orders_items_data=pd.merge(orders_data, df_oi, on='order_id', how='inner',suffixes=('_orders','_order_items'))
    products_data=df_p[['product_id','product_name']]
    orders_items_products=pd.merge(orders_items_data, products_data, on='product_id', how='inner')
    orders_items_products=orders_items_products[orders_items_products.items_purchased>1]

    order_products=orders_items_products.groupby('order_id')['product_name'].apply(list)


    pairs = []
    for products in order_products:
        products = list(set(products))  # avoid duplicate items within same order
        if len(products) > 1:
            pairs += list(combinations(products, 2))

    # Step 3: count most common pairs
    cross_sell_counts = Counter(pairs)

    # Step 4: create a DataFrame for better viewing
    cross_sell_df = pd.DataFrame(cross_sell_counts.items(), columns=['product_pair', 'count'])
    cross_sell_df = cross_sell_df.sort_values(by='count', ascending=False).reset_index(drop=True)

    cross_sell_df['product_pair']=cross_sell_df['product_pair'].apply(lambda x: x[0]+ "+" +x[1])
    cross_sell_df['count_pct']=round(cross_sell_df['count']/cross_sell_df['count'].sum()*100,2)

# Step 4: Gradient Column Chart
    fig_cross = px.bar(
    cross_sell_df,
    x='product_pair',
    y='count_pct',
    title="Cross-Sell Product Pairs (%)",
    text='count_pct',
    labels={'product_pair': 'Product Pair', 'count_pct': 'Percentage (%)'},
    color='count_pct',
    color_continuous_scale='Viridis'
)

    fig_cross.update_traces(texttemplate='%{text}%', textposition='auto')

    fig_cross.update_layout(
    yaxis_title='Share (%)',
    xaxis_title='Product Pair',
    coloraxis_showscale=False,xaxis_tickangle=20
)

    st.plotly_chart(ut.style_chart(fig_cross), use_container_width=True)



    #quantity sold distribution by device 




    orders_sessions = df_o.merge(
    df_s[['website_session_id', 'device_type']],
    on='website_session_id',
    how='left'
)

# Step 2: Join with order_items to get product-level quantities
    order_items_full = orders_sessions.merge(
    df_oi,
    on='order_id',
    how='inner'
)

# Step 3: Join with product master to bring product names
    order_items_full = order_items_full.merge(
    df_p[['product_id', 'product_name']],
    on='product_id',
    how='left'
)

# Step 4: Calculate quantity sold by product × device
    qty_dist = (
    order_items_full.groupby(['product_name', 'device_type'])['order_item_id']
    .count()
    .reset_index(name='units_sold')
)

# Step 5: Convert to % distribution within each product
    qty_dist['pct'] =((qty_dist['units_sold']/qty_dist['units_sold'].sum())*100).round(2)
    qty_dist.sort_values(by='pct',inplace=True,ascending=False)
# Step 6: Clustered Column (Grouped Bar) Chart
    fig = px.bar(
    qty_dist,
    x='product_name',
    y='pct',
    color='device_type',
    barmode='group',
    text='pct',
    title='Quantity Sold Distribution by Product and Device Type (%)',
    labels={
        'pct': 'Share (%)',
        'product_name': 'Product',
        'device_type': 'Device Type'
    }
)

    fig.update_traces(textposition='auto',texttemplate='%{text}%')
    fig.update_layout(xaxis_tickangle=0)

    st.plotly_chart(ut.style_chart(fig), use_container_width=True)