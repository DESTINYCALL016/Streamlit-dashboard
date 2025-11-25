import pandas as pd
import streamlit as st
import os
import numpy as np
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def _build_path(file_name):
    return os.path.join(SCRIPT_DIR, file_name)

def _try_read(paths):
    for p in paths:
        try:
            if p.endswith('.csv'): return pd.read_csv(p)
            elif p.endswith('.xlsx'): return pd.read_excel(p)
        except FileNotFoundError: continue
    st.error(f"File not found: {paths[0]}")
    st.stop()

@st.cache_data
def load_data():
    # 1. Load
    df_s = _try_read([_build_path('website_sessions.csv')])
    df_o = _try_read([_build_path('orders.csv')])
    df_oi = _try_read([_build_path('order_items.csv')])
    df_p = _try_read([_build_path('products.csv')])
    df_r = _try_read([_build_path('order_item_refunds.csv')])
    df_pv = _try_read([_build_path('website_pageviews.csv')]) # Load Pageviews

    # 2. Dates
    for df in [df_s, df_o, df_oi, df_p, df_r, df_pv]:
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')

    # 3. Cleaning

    utm_source_2=[]

    for i in df_s.http_referer:
        if i=="https://www.gsearch.com":
            utm_source_2.append("gsearch")
        elif i=="https://www.bsearch.com":
            utm_source_2.append("bsearch")
        elif i=="https://www.socialbook.com":
            utm_source_2.append("socialbook")
        else:
            utm_source_2.append(np.nan)

    utm_source_2=pd.Series(utm_source_2)
    df_s["utm_source"]=utm_source_2

# print(website_sessions.isna().sum()/website_sessions.shape[0]*100)    #crossing the threshold of 5%

    df_s.fillna("Untracked",inplace=True)





    
    # if 'utm_source' not in df_s.columns: df_s['utm_source'] = 'untracked'
    # df_s['utm_source'] = df_s['utm_source'].fillna('untracked')
    
    # Margins
    df_oi['price_usd'] = pd.to_numeric(df_oi['price_usd']).fillna(0)
    df_oi['cogs_usd'] = pd.to_numeric(df_oi['cogs_usd']).fillna(0)
    df_oi['margin'] = df_oi['price_usd'] - df_oi['cogs_usd']
    
    refund_ids = df_r['order_item_id'].unique()
    df_oi['is_refunded'] = df_oi['order_item_id'].isin(refund_ids)
    
    # Join Orders
    if 'order_id' in df_oi.columns:
        order_agg = df_oi.groupby('order_id').agg(
            revenue=('price_usd', 'sum'),
            margin=('margin', 'sum'),
            items=('order_item_id', 'count')
        ).reset_index()
        df_full = df_o.merge(order_agg, on='order_id', how='left').fillna(0)
    else:
        df_full = df_o.copy()

    # Product Names
    if 'product_name' not in df_p.columns:
        df_p['product_name'] = 'Product ' + df_p['product_id'].astype(str)

    return df_s, df_full, df_oi, df_p, df_pv

