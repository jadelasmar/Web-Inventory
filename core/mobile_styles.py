"""Mobile-friendly CSS styles for the app."""
import streamlit as st


def apply_mobile_styles():
    """Apply mobile-responsive CSS styles."""
    st.markdown("""
    <style>
    /* Expand main content when sidebar is collapsed */
    section[data-testid="stSidebar"][aria-expanded="false"] ~ div[data-testid="stAppViewContainer"] {
        margin-left: 0 !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="false"] {
        margin-left: -18rem !important;
    }
    
    /* Fix sidebar width */
    section[data-testid="stSidebar"] {
        width: 18rem !important;
        min-width: 18rem !important;
        max-width: 18rem !important;
    }
    
    /* Hide only the resize handle cursor */
    section[data-testid="stSidebar"] > div:first-child {
        cursor: default !important;
    }
    
    /* Mobile-friendly adjustments */
    @media (max-width: 768px) {
        /* Larger touch targets for buttons */
        .stButton button {
            min-height: 48px !important;
            font-size: 16px !important;
            padding: 12px 24px !important;
        }
        
        /* Better spacing for mobile */
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Form inputs - prevent zoom on iOS */
        input, select, textarea {
            font-size: 16px !important;
        }
        
        /* Better table scrolling */
        .dataframe {
            overflow-x: auto !important;
            display: block !important;
        }
    }
    
    /* Always scrollable tables */
    .dataframe {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)
