import streamlit as st
import pandas as pd
import auth
import data_loader as dl
import utils as ut
# Import all views
from views import business, website, marketing, product

# 1. Page Config
st.set_page_config(page_title="Digital Analytics", page_icon="📊", layout="wide")
ut.load_css()

# 2. Auth
if not auth.check_password():
    st.stop()

# 3. Load Data (Returns 5 DataFrames now)
df_sess, df_orders, df_items, df_prods, df_pv = dl.load_data()

# 4. Sidebar
st.sidebar.title("Navigation")
st.sidebar.info(f"User: {st.session_state['current_user']}")





#########################
 # 5. Global Date Filter
st.sidebar.markdown("---")
min_date = df_sess['created_at'].min().date()
max_date = df_sess['created_at'].max().date()
start_date, end_date = st.sidebar.date_input("Date Range", [min_date, max_date])

# 6. Filter Data
start_ts = pd.to_datetime(start_date)
end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1)

# Apply filters to sessions/orders/items/pageviews
df_s_filt = df_sess[(df_sess['created_at'] >= start_ts) & (df_sess['created_at'] < end_ts)]
df_o_filt = df_orders[(df_orders['created_at'] >= start_ts) & (df_orders['created_at'] < end_ts)]
df_i_filt = df_items[(df_items['created_at'] >= start_ts) & (df_items['created_at'] < end_ts)]
df_pv_filt = df_pv[df_pv['website_session_id'].isin(df_s_filt['website_session_id'])]











# Updated Menu
page = st.sidebar.radio("Go to", [
    "Business Overview", 
    "Website Performance", 
    "Marketing Performance", 
    "Product Dashboard"
])

















#######################################################################

# --- Additional Slicers ---
st.sidebar.markdown("### Filters")

# UTM Source slicer
utm_sources = df_sess['utm_source'].fillna('Untracked').unique().tolist()
selected_utm = st.sidebar.multiselect(
    "UTM Source",
    options=utm_sources,
    default=utm_sources
)

# Product ID slicer
product_ids = df_prods['product_id'].unique().tolist()
selected_product_ids = st.sidebar.multiselect(
    "Product ID",
    options=product_ids,
    default=product_ids
)





# --- UTM source filter ---
df_s_filt = df_s_filt[
    df_s_filt['utm_source'].isin(selected_utm)
]

# --- Filter orders based on filtered sessions ---
df_o_filt = df_o_filt[
    df_o_filt['website_session_id'].isin(df_s_filt['website_session_id'])
]

# --- Filter items based on remaining orders ---
df_i_filt = df_i_filt[
    df_i_filt['order_id'].isin(df_o_filt['order_id'])
]

# --- Add product info (safe merge) ---
df_i_filt = df_i_filt.merge(
    df_prods[['product_id']],
    on='product_id',
    how='left'
)

# --- Product name slicer ---
df_i_filt = df_i_filt[
    df_i_filt['product_id'].isin(selected_product_ids)
]

# --- Pageviews follow sessions ---
df_pv_filt = df_pv[df_pv['website_session_id'].isin(df_s_filt['website_session_id'])]





# 7. Routing Logic
if page == "Business Overview":
    business.show(df_s_filt, df_o_filt, df_i_filt, df_prods, df_pv)
elif page == "Website Performance":
    website.show(df_s_filt, df_o_filt, df_pv_filt)
elif page == "Marketing Performance":
    marketing.show(df_s_filt, df_o_filt,df_pv)
elif page == "Product Dashboard":
    product.show(df_i_filt, df_prods, df_pv,df_o_filt,df_s_filt)












# Logout
st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    st.session_state["password_correct"] = False
    st.rerun()