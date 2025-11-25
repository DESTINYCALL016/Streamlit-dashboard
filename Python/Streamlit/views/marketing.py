from matplotlib.pyplot import yticks
import streamlit as st
import pandas as pd
import plotly.express as px
import utils as ut

def show(df_s, df_o,df_pv):
    st.subheader("📣 Marketing Performance")

    # --- CRITICAL FIX: Merge Orders with Session Data ---
    # We merge to get 'utm_source' and 'is_repeat_session' attached to every order
    df_o_enriched = df_o.merge(
        df_s[['website_session_id', 'utm_source', 'is_repeat_session']], 
        on='website_session_id', 
        how='left'
    )

    # --- 1. Logic & KPIs ---
    total_visitors = df_s['user_id'].nunique()
    total_sessions = df_s['website_session_id'].nunique()
    
    # G-Search Stats
    # Count sessions where source is gsearch
    g_sessions = len(df_s[df_s['utm_source'] == 'gsearch'])
    # Count orders where source is gsearch (using the enriched dataframe)
    g_orders = len(df_o_enriched[df_o_enriched['utm_source'] == 'gsearch'])
    
    g_cvr = g_orders / g_sessions if g_sessions > 0 else 0
    
    # Repeat Stats
    # We check for column existence to avoid errors if data is missing
    if 'is_repeat_session' in df_s.columns:
        repeat_sessions = df_s[df_s['is_repeat_session'] == 1].shape[0]
        repeat_visitors = df_s[df_s['is_repeat_session'] == 1]['user_id'].nunique()
    else:
        repeat_sessions = 0
        repeat_visitors = 0
    
    # Rev / Session
    # rps = df_o_enriched['revenue'].sum() / total_sessions if total_sessions > 0 else 0

    # Display Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    ut.kpi_card(c1, "G-Search Sessions %", f"{g_sessions/total_sessions:.2%}")
    ut.kpi_card(c2, "G-Search CVR", f"{g_cvr:.2%}")
    ut.kpi_card(c3, "Total Visitors", f"{total_visitors/1000:,.2f}K")
    ut.kpi_card(c4, "Repeat Visitors %", f"{repeat_visitors/total_visitors:.2%}")
    ut.kpi_card(c5, "Repeat Sessions %", f"{repeat_sessions/total_sessions:.2%}")
   

  
    
###sessions distribution 

    df_s2 = df_s.copy()
    df_s2['year_month'] = df_s2['created_at'].dt.to_period('M').astype(str)

    monthly_source = (
    df_s2.groupby(['year_month', 'utm_source'])['website_session_id']
    .nunique()
    .reset_index(name='sessions')
)
    monthly_source['sessions']=(monthly_source['sessions'].round(2)/1000).round(2)

    fig = px.line(
    monthly_source,
    x='year_month',
    y='sessions',
    color='utm_source',
    markers=True,
    title='Monthly Sessions by UTM Source'
)

    fig.update_layout(
    xaxis_title='Month-Year',
    yaxis_title='Sessions in thousands',
    legend_title='UTM Source',
    legend=dict(orientation='h', y=-0.25)
)

    st.plotly_chart(fig, use_container_width=True)



###Revenue by channel and campaign###

    orders = df_o.copy()
    sessions = df_s.copy()

# Merge orders with sessions for attribution
    merged = orders.merge(
    sessions[['website_session_id', 'utm_source', 'utm_campaign']],
    on='website_session_id',
    how='left'
)

# Fill missing attribution if needed
# merged['utm_source'] = merged['utm_source'].fillna('Untracked')
# merged['utm_campaign'] = merged['utm_campaign'].fillna('Untracked')

# --- Step 1: Combine source and campaign into one label with newline ---
    merged['source_campaign'] = merged['utm_source'] + "\n" + merged['utm_campaign']

# --- Step 2: Total revenue per combined label ---
    rev = (
    merged.groupby('source_campaign')['revenue']
    .sum()
    .reset_index()
)

# --- Step 3: Calculate overall revenue % ---
    rev['revenue_pct'] = ((rev['revenue'] / rev['revenue'].sum()) * 100).round(2)
    rev.sort_values(by='revenue_pct', ascending=False,inplace=True)

# --- Step 4: Column chart ---
    

    fig = px.bar(
    rev,
    x='source_campaign',
    y='revenue_pct',
    text='revenue_pct',
    title='Overall Revenue Distribution (%) by Source & Campaign',
    color='revenue_pct',
    color_continuous_scale='Blues'
)

    fig.update_traces(textposition='auto',texttemplate='%{text}%')
    fig.update_layout(
    xaxis_title='Source & Campaign',
    yaxis_title='Revenue (%)')

    st.plotly_chart(fig, use_container_width=True)
        


########repeat sssion rate by source and campaign########

    
    df_r = df_s.copy()

# Handle missing values
    df_r['utm_source'] = df_r['utm_source'].fillna('Untracked')
    df_r['utm_campaign'] = df_r['utm_campaign'].fillna('Untracked')

# Combined label
    df_r['source_campaign'] = df_r['utm_source'] + "\n" + df_r['utm_campaign']

# --- Step 1: Total sessions per source+campaign ---
    total_sessions = (
    df_r.groupby('source_campaign')['website_session_id']
    .nunique()
    .reset_index(name='total_sessions')
)

# --- Step 2: Repeat sessions per source+campaign ---
    repeat_sessions = (
    df_r[df_r['is_repeat_session'] == 1]
    .groupby('source_campaign')['website_session_id']
    .nunique()
    .reset_index(name='repeat_sessions')
)

# --- Step 3: Merge ---
    repeat_stats = total_sessions.merge(repeat_sessions, on='source_campaign', how='left')
    repeat_stats['repeat_sessions'] = repeat_stats['repeat_sessions'].fillna(0)

# --- Step 4: Calculate repeat session rate ---
    repeat_stats['repeat_rate'] = ((repeat_stats['repeat_sessions'] / repeat_stats['total_sessions']) * 100).round(2)
    repeat_stats.sort_values(by='repeat_rate', ascending=False,inplace=True)

# --- Visualization (Bar Chart) ---
    fig = px.bar(
    repeat_stats,
    x='source_campaign',
    y='repeat_rate',
    text='repeat_rate',
    title='Repeat Session Rate by Source & Campaign in %',
    color='repeat_rate',
    color_continuous_scale='Viridis'
)

    fig.update_traces(textposition='auto',texttemplate='%{text}%')
    fig.update_layout(
    xaxis_title='Source & Campaign',
    yaxis_title='Repeat Session Rate (%)'
)

    st.plotly_chart(fig, use_container_width=True)






    # Row 2
    c_left, c_right = st.columns(2)

    with c_left:
        # Campaign Performance
        pv = df_pv.copy()
        s = df_s.copy()

# Fill missing sources
        # s['utm_source'] = s['utm_source'].fillna('Untracked')

# --- Step 1: Calculate page depth per session ---
        page_depth = (
        pv.groupby('website_session_id')['pageview_url']
        .count()
        .reset_index(name='page_depth')
)

# --- Step 2: Merge with session table to get source ---
        merged = page_depth.merge(
        s[['website_session_id', 'utm_source']],
        on='website_session_id',
        how='left'
)

# --- Step 3: Average page depth per source ---
        avg_depth = (
        merged.groupby('utm_source')['page_depth']
        .mean()
        .reset_index(name='avg_page_depth')
)

        avg_depth['avg_page_depth'] = avg_depth['avg_page_depth'].round(2)
        avg_depth.sort_values(by='avg_page_depth', ascending=False,inplace=True)

# --- Visualization ---
        fig = px.bar(
        avg_depth,
        x='utm_source',
        y='avg_page_depth',
        text='avg_page_depth',
        title='Average Page Depth per UTM Source',
        color='avg_page_depth',
        color_continuous_scale='Viridis'
)

        fig.update_traces(textposition='auto')

        fig.update_layout(
        xaxis_title='UTM Source',
        yaxis_title='Avg Page Depth'
)

        st.plotly_chart(fig, use_container_width=True)





    with c_right:
        # Session Frequency
        df_s2 = df_s.copy()

# --- Step 1: Count sessions per user ---
        user_freq = (
        df_s2.groupby('user_id')['website_session_id']
        .nunique()
        .reset_index(name='session_count'))

# --- Step 2: Create distribution ---
        freq_dist = (
        user_freq.groupby('session_count')['user_id']
        .count()
        .reset_index(name='num_users'))

# --- Step 3: Convert to % ---
        freq_dist['pct_users'] = (freq_dist['num_users'] / freq_dist['num_users'].sum() * 100).round(2)
        freq_dist.sort_values(by='pct_users', ascending=False,inplace=True)

# --- Visualization (bar chart) ---
        fig = px.bar(
        freq_dist,
        x='session_count',
        y='pct_users',
        text='pct_users',
        title='Session Frequency Distribution by Users (%)',
        labels={'session_count': 'Number of Sessions', 'pct_users': 'Users (%)'})

        fig.update_traces(textposition='auto',texttemplate='%{text}%')

        fig.update_layout(
        xaxis_title='Sessions per User',
        yaxis_title='Percentage of Users (%)')

        st.plotly_chart(fig, use_container_width=True)



    c1,c2 = st.columns(2)

    with c1:
        ##conversion rate##
        df_s2 = df_s.copy()
        df_o2 = df_o.copy()

        # Fill missing source
        # df_s2['utm_source'] = df_s2['utm_source'].fillna('Untracked')

        # --- Step 1: Count sessions per source ---
        sessions_per_source = (
            df_s2.groupby('utm_source')['website_session_id']
            .nunique()
            .reset_index(name='sessions')
)

        # --- Step 2: Count orders per source ---
        orders_per_source = (
            df_s2.merge(
        df_o2[['website_session_id', 'order_id']],
        on='website_session_id',
        how='inner'
    )
    .groupby('utm_source')['order_id']
    .nunique()
    .reset_index(name='orders')
)

        # --- Step 3: Merge and calculate conversion rate ---
        conv_df = sessions_per_source.merge(orders_per_source, on='utm_source', how='left')
        conv_df['orders'] = conv_df['orders'].fillna(0)

        conv_df['conversion_rate'] = (
            conv_df['orders'] / conv_df['sessions'] * 100
        ).round(2)
        conv_df.sort_values(by='conversion_rate', ascending=False,inplace=True)

        # --- Step 4: Bar chart ---
        fig = px.bar(
            conv_df,
            x='utm_source',
            y='conversion_rate',
            text='conversion_rate',
            title='Conversion Rate by UTM Source (%)',
            labels={'utm_source': 'UTM Source', 'conversion_rate': 'Conversion Rate (%)'},color_continuous_scale='Viridis'
)

        fig.update_traces(texttemplate='%{text}%', textposition='auto')

        fig.update_layout(
            yaxis_title='Conversion Rate (%)',
            xaxis_title='UTM Source'
        )

        st.plotly_chart(ut.style_chart(fig), use_container_width=True)

    with c2:
        ##repeat vs new users
        df_s2 = df_s.copy()
        # df_s2['utm_source'] = df_s2['utm_source'].fillna('Untracked')

        # --- Total users ---
        total_users = (
            df_s2.groupby('utm_source')['user_id']
            .nunique()
            .reset_index(name='total_users')
)

        # --- Repeat users ---
        repeat_users = (
            df_s2[df_s2['is_repeat_session'] == 1]
            .groupby('utm_source')['user_id']
            .nunique()
            .reset_index(name='repeat_users')
)

        # --- Merge ---
        user_df = total_users.merge(repeat_users, on='utm_source', how='left')
        user_df['repeat_users'] = user_df['repeat_users'].fillna(0)

        # --- Calculate repeat % ---
        user_df['repeat_pct'] = (
            user_df['repeat_users'] / user_df['total_users'] * 100
        ).round(2)

   
        fig = px.bar(
            user_df,
            x='utm_source',
            y='repeat_pct',
            text='repeat_pct',
            title='Repeat Users in % by Source',
            labels={'repeat_pct': 'Repeat Users %', 'utm_source': 'Source'},color_continuous_scale='viridis'
        )

        fig.update_traces(texttemplate='%{text}%', textposition='auto')

        fig.update_layout(
            yaxis_title='Repeat Users (%)',
            xaxis_title='UTM Source'
)

        st.plotly_chart(ut.style_chart(fig), use_container_width=True)

























