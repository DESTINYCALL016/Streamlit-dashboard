import streamlit as st
import plotly.graph_objects as go

def load_css():
    # Theme Color: Pinkish Red (#FF2B4A)
    # Backgrounds: Light Pink Theme
    st.markdown("""
    <style>
        /* Main Background */
        .stApp {
            background-color: #FFF1F3; /* Very Light Pink */
            color: #333333; /* Dark text for contrast */
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF; /* White Sidebar */
            border-right: 1px solid #FFE4E8;
        }

        /* Cards */
        .kpi-card {
            background-color: #FFFFFF; /* White Cards */
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #FF2B4A; /* Accent Border */
            box-shadow: 0 4px 6px rgba(0,0,0,0.05); /* Soft Shadow */
            text-align: center;
            margin-bottom: 10px;
        }

        /* Text Styling inside Cards */
        .kpi-title {
            font-size: 14px;
            color: #666666; /* Dark Grey */
            margin-bottom: 5px;
        }
        .kpi-value {
            font-size: 24px;
            font-weight: bold;
            color: #333333; /* Black/Dark Grey */
        }

        /* Login Form Input Fields */
        .stTextInput input {
            color: #333333;
            background-color: #FFFFFF;
            border: 1px solid #FFB3C1;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background-color: #FFFFFF;
            border-radius: 5px 5px 0px 0px;
            padding: 0px 20px;
            color: #666666; /* Dark Grey Text */
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stTabs [aria-selected="true"] {
            background-color: #FF2B4A; /* Pinkish Red Active Tab */
            color: #FFFFFF !important;
            font-weight: bold;
        }
        
        /* Metrics in standard streamlit view */
        [data-testid="stMetricLabel"] { color: #666666; }
        [data-testid="stMetricValue"] { color: #333333; }
    </style>
    """, unsafe_allow_html=True)

def kpi_card(col, title, value, prefix="", suffix=""):
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{prefix}{value}{suffix}</div>
    </div>
    """, unsafe_allow_html=True)

def style_chart(fig):
    fig.update_layout(
        # Updated chart backgrounds to match the new Light theme
        paper_bgcolor='#FFFFFF', # White background for charts
        plot_bgcolor='#FFFFFF',
        font_color='#333333', # Dark text
        title_font_color='#FF2B4A', # Pinkish Red Chart Titles
        xaxis=dict(showgrid=False, color='#666666'),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0', color='#666666'), # Very subtle grey grid lines
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig