import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import utils as ut

def show(df_s, df_o, df_pv):
    st.subheader("🌐 Website Performance Dashboard")

    if df_pv.empty:
        st.warning("No pageview data available.")
        return

    # ==============================================================================
    # 1. LOGIC & DATA PROCESSING
    # ==============================================================================
    
    # --- Merge for Metrics ---
    sess_data = df_s.merge(df_o[['website_session_id', 'revenue']], on='website_session_id', how='left')
    sess_data['is_converted'] = sess_data['revenue'].notnull()
    sess_data['revenue'] = sess_data['revenue'].fillna(0)

    # --- KPI Calculations ---
    
    # 1. Total Sessions
    total_sessions = df_s['website_session_id'].count()
    
    # 2. Bounce Rate (Sessions with only 1 pageview)
    pv_counts = df_pv.groupby('website_session_id').size()
    bounces = pv_counts[pv_counts == 1].count()
    bounce_rate = bounces / total_sessions if total_sessions > 0 else 0
    
    # 3. Conversion Rate
    total_orders = df_o['website_session_id'].nunique()
    cvr = total_orders / total_sessions if total_sessions > 0 else 0
    
    # 4. Avg Pages per Session (Engagement)
    avg_pages = len(df_pv) / total_sessions if total_sessions > 0 else 0
    
    # 5. Revenue per Session
    rps = sess_data['revenue'].sum() / total_sessions if total_sessions > 0 else 0

    # ==============================================================================
    # 2. KPI CARDS (Row 1)
    # ==============================================================================
    c1, c2, c3, c4, c5 = st.columns(5)
    ut.kpi_card(c1, "Total Sessions", f"{total_sessions/1000:,.2f}K")
    ut.kpi_card(c2, "Bounce Rate", f"{bounce_rate:.1%}")
    ut.kpi_card(c3, "Conversion Rate", f"{cvr:.2%}")
    ut.kpi_card(c4, "Avg Pages/Sess", f"{avg_pages:.2f}")
    ut.kpi_card(c5, "Rev / Session", f"{rps:.2f}", "$")


   
    
  
        # CHART 1: Daily Traffic Trend (Area Chart)
       
    df_s['year'] = df_s['created_at'].dt.year
    df_s['month'] = df_s['created_at'].dt.month

    # Group sessions by month-year
    monthly_sess = df_s.groupby(['year', 'month'])['website_session_id'].count().reset_index()
    monthly_sess['year_month'] = monthly_sess['year'].astype(str) + "-" + monthly_sess['month'].astype(str)

    # Convert to percentage of total sessions
    total_sessions = monthly_sess['website_session_id'].sum()
    monthly_sess['Sessions_pct'] = ((monthly_sess['website_session_id'] / total_sessions) * 100).round(2)

    # Plot
    fig_sess_pct = px.line(
    monthly_sess,
    x='year_month',
    y='Sessions_pct',
    markers=True,
    title="Sessions Trends Over Time"
)

    # Y axis in %
    fig_sess_pct.update_yaxes(ticksuffix="%")

    st.plotly_chart(ut.style_chart(fig_sess_pct), use_container_width=True)

    







        # CHART 2: Device Breakdown (Donut Chart)
    c1,c2=st.columns(2)
    with c1:
     

    # Total sessions by device
      device_stats = df_s.groupby('device_type')['website_session_id'].count().reset_index()
      device_stats.columns = ['Device', 'Sessions']

    # Conversion mapping
      conv_stats = pd.merge(df_s, df_o, on='website_session_id', how='inner')
    
    # Conversion rate by device
      conv_stats = conv_stats.groupby('device_type')['website_session_id'].count().reset_index()
      conv_stats.columns = ['Device', 'Conversions']

    # Merge both
      final = device_stats.merge(conv_stats, on='Device').reset_index(drop=True)    
     
    # Convert CVR to %
      final['CVR_pct'] = ((final['Conversions'] / final['Sessions']) * 100).round(2)
      final['Sessions_in_thousands']=(final['Sessions']/1000).round(2)

    # Clustered column chart
      fig_dev = px.bar(
        final,
        x='Device',
        y=['Sessions_in_thousands', 'CVR_pct'],
        barmode='group',
        title="Sessions Distribution & Conversion Rate by Device Type",
        text_auto='.2f',color_discrete_sequence=['Blue', 'Green']
    )

    # Y-axis labels
      fig_dev.update_layout(
        yaxis_title="Sessions in thousands",
        legend_title="Metric",
        legend=dict(orientation="h", y=-0.2)
    )

    # If you want CVR to plot on secondary axis
      fig_dev.update_traces(selector=dict(name='CVR_pct'), yaxis='y2')
      fig_dev.update_layout(
        yaxis2=dict(overlaying='y', side='right', title="CVR (%)")
    )
      fig_dev.update_traces(textposition="auto")
      st.plotly_chart(ut.style_chart(fig_dev), use_container_width=True)



    # conversion funnel

    with c2:
        def map_page(url):
            if url.startswith("/lander") or url == "/home":
                return "/homepages"
            elif url == "/products":
                return "/products"
            elif url in [
                "/the-original-mr-fuzzy",
                "/the-forever-love-bear",
                "/the-birthday-sugar-panda",
                "/the-hudson-river-mini-bear"
            ]:
                return "/one_of_the_product_page"
            elif url == "/cart":
                return "/cart"
            elif url == "/shipping":
                return "/shipping"
            elif url.startswith("/billing"):
                return "/billing"
            elif url == "/thank-you-for-your-order":
                return "/thank-you-for-your-order"
            else:
                return None

        df = df_pv.copy()
        df["funnel_stage"] = df["pageview_url"].apply(map_page)
        df = df.dropna(subset=["funnel_stage"])

        # Count pageviews
        funnel = df.groupby("funnel_stage").size().reset_index(name="visits")

        funnel = funnel.sort_values("visits", ascending=False).reset_index(drop=True)

        # Funnel percentage
        top_visits = funnel["visits"].iloc[0]
        funnel["funnel_pct"] = (funnel["visits"] / top_visits * 100).round(2)


        fig = px.funnel(
            funnel,
            x="visits",
            y="funnel_stage",
            title="Conversion Funnel",
            text="funnel_pct"
        )

        fig.update_traces(texttemplate="%{text}%", textposition="auto")

        st.plotly_chart(fig, use_container_width=True)







#####landing page performance
    c3,c4=st.columns(2)
    # with c_right:
    with c3:
       first_pv = df_pv.sort_values("created_at").groupby("website_session_id").first().reset_index()

       df_lp = first_pv[["website_session_id", "pageview_url"]].rename(columns={
    "pageview_url": "landing_page"}) 
       lp_sessions = df_lp.groupby("landing_page")["website_session_id"].count().reset_index()
       lp_sessions.columns = ["Landing Page", "Sessions"]
    
       total_sessions = lp_sessions["Sessions"].sum()
       lp_sessions["Sessions_pct"] = (lp_sessions["Sessions"] / total_sessions * 100).round(2)
       conv = df_lp.merge(df_o, on="website_session_id", how="inner")
       lp_conv = conv.groupby("landing_page")["website_session_id"].count().reset_index()
       lp_conv.columns = ["Landing Page", "Conversions"]
       final_lp = lp_sessions.merge(lp_conv, on="Landing Page")
       final_lp["CVR_pct"] = ((final_lp["Conversions"] / final_lp["Sessions"]) * 100).round(2)

       final_lp = final_lp.sort_values("Sessions", ascending=False)
       fig = px.bar(
    final_lp,
    x="Landing Page",
    y=["Sessions_pct", "CVR_pct"],
    barmode="group",
    title="Landing Pages Performance: Sessions Distribution and Conversion Rate",
    text_auto=".1f",
    color_continuous_scale=['Blue', 'Green']
)

       fig.update_layout(
       yaxis_title="Percentage (%)",
       legend_title="Metrics",
       legend=dict(orientation="h", y=-0.25),
       xaxis_tickangle=0
)
       fig.update_traces(textposition="auto")
       st.plotly_chart(fig, use_container_width=True)




######bounce rate 
    with c4:
        # 1. Identify landing page (first pageview per session)
       first_pv = (
           df_pv.sort_values("created_at")
         .groupby("website_session_id")
         .first()
         .reset_index()
)

       first_pv = first_pv[["website_session_id", "pageview_url"]].rename(
           columns={"pageview_url": "landing_page"}
       )

       # 2. Pageviews count per session
       pv_counts = df_pv.groupby("website_session_id").size().reset_index(name="pv_count")

       # 3. Merge landing page + pv count
       df_lp = first_pv.merge(pv_counts, on="website_session_id", how="left")

       # 4. Mark bounces (1 pageview = bounce)
       df_lp["is_bounce"] = df_lp["pv_count"] == 1

       # 5. Bounce rate per landing page
       bounce_stats = df_lp.groupby("landing_page").agg(
           Sessions=("website_session_id", "count"),
           Bounces=("is_bounce", "sum")
       ).reset_index()

       bounce_stats["Bounce_Rate_pct"] = (
           bounce_stats["Bounces"] / bounce_stats["Sessions"] * 100
       ).round(2)

       bounce_stats = bounce_stats.sort_values("Bounce_Rate_pct", ascending=False)



       fig_bounce = px.bar(
           bounce_stats,
           x="landing_page",
           y="Bounce_Rate_pct",
           title="Bounce Rate by Landing Page",
           text_auto=".2f",
           color="Bounce_Rate_pct",
           color_continuous_scale="Reds"
       )

       fig_bounce.update_layout(
           yaxis_title="Bounce Rate",
           xaxis_title="Landing Page",
           xaxis_tickangle=0,
           coloraxis_showscale=False
       )
       fig_bounce.update_traces(textposition="auto")
       st.plotly_chart(ut.style_chart(fig_bounce), use_container_width=True)




    # --- top website pages ---
    # CHART 5: 
    # Make copies
    pageviews = df_pv.copy()
    sessions = df_s.copy()

    # Total number of sessions
    total_sessions = sessions['website_session_id'].nunique()

    # Count pageviews per page
    page_stats = (
    pageviews['pageview_url']
    .value_counts()
    .reset_index()
)

    page_stats.columns = ['page', 'visits']

    # Convert visits to % of total sessions
    page_stats['visit_pct'] = (page_stats['visits'] / total_sessions * 100).round(2)

    # Optional: show top 15 pages
    page_stats = page_stats.head(15)



    fig_pages = px.bar(
    page_stats,
    x='page',
    y='visit_pct',
    title='Top Website Pages (% of Sessions)',
    text_auto='.1f',
    color='visit_pct',
    color_continuous_scale='Greens'
)

    fig_pages.update_layout(
    yaxis_title='Visits (%)',
    xaxis_title='Website Pages',
    xaxis_tickangle=-30,
    coloraxis_showscale=False
)

    st.plotly_chart(ut.style_chart(fig_pages), use_container_width=True)



####exit rate of website pages

    pv = df_pv.copy()
    pv['created_at'] = pd.to_datetime(pv['created_at'])

    pv = pv.sort_values(by=['website_session_id', 'created_at'])
    pv['is_exit'] = pv.groupby('website_session_id')['pageview_url'].transform(lambda x: (x == x.iloc[-1]).astype(int))

    page_visits = pv['pageview_url'].value_counts().reset_index()
    page_visits.columns = ['page', 'total_visits']

    exit_counts = pv[pv['is_exit'] == 1]['pageview_url'].value_counts().reset_index()
    exit_counts.columns = ['page', 'exit_count']

    exit_rate = page_visits.merge(exit_counts, on='page', how='left')
    exit_rate['exit_count'] = exit_rate['exit_count'].fillna(0)
    exit_rate['exit_rate'] = ((exit_rate['exit_count'] / exit_rate['total_visits'])* 100).round(2)
    exit_rate = exit_rate.sort_values(by='exit_rate', ascending=False)

    fig_exit = px.bar(
    exit_rate,
    x='page',
    y='exit_rate',
    title='Exit Rate(in %) by Website Pages',
    text='exit_rate',
    labels={'exit_rate': 'Exit Rate (%)', 'page': 'Page'})


    fig_exit.update_layout(
    xaxis_title='Page',
    yaxis_title='Exit Rate(%)',
    xaxis_tickangle=-30,
    coloraxis_showscale=False)
    
    st.plotly_chart(ut.style_chart(fig_exit), use_container_width=True)




    ###bounce rate trends

 # Pageviews per session
    pv_counts = df_pv.groupby("website_session_id").size()

# Bounced session IDs (exactly 1 pageview)
    bounced_sessions = pv_counts[pv_counts == 1].index

# Add bounce flag to session table
    df_s['is_bounced'] = df_s['website_session_id'].isin(bounced_sessions)

# Create Year-Month column
    df_s['year_month'] = df_s['created_at'].dt.to_period('M').astype(str)

# Bounce rate by Year-Month
    bounce_trend = (
    df_s.groupby('year_month')['is_bounced']
    .mean()
    .reset_index()
)

    bounce_trend['bounce_pct'] = (bounce_trend['is_bounced'] * 100).round(2)



    fig_bounce = px.line(
    bounce_trend,
    x='year_month',
    y='bounce_pct',
    markers=True,
    title='Bounce Rate Trend Over Time (%)'
)

    fig_bounce.update_traces(line_width=3)

    fig_bounce.update_layout(
    yaxis_title='Bounce Rate (%)',
    coloraxis_showscale=False   
)


    st.plotly_chart(ut.style_chart(fig_bounce), use_container_width=True)




