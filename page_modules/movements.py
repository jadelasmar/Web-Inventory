"""Movement log page to view transaction history."""
import streamlit as st
from core.constants import MOVEMENT_TYPES
from core.services import get_movements, delete_movement
from core.simple_auth import get_current_user


def render(conn):
    """Render the movement log page."""
    st.header("🔄 Movement Log")
    days = st.selectbox("Last", [1, 7, 30, 90, "All"])
    types = st.multiselect("Type", MOVEMENT_TYPES, default=MOVEMENT_TYPES)
    days_val = None if days == "All" else days
    df = get_movements(conn, days_val, types)
    
    # Keep the original ID column for deletion
    df_with_id = df.copy()
    search = st.text_input("Search by name, category, or supplier")
    if not df.empty:
        # Case-insensitive partial search across product_name, product_category, supplier_customer
        if search:
            mask = (
                df["product_name"].str.contains(search, case=False, na=False)
                | df["product_category"].str.contains(search, case=False, na=False)
                | df["supplier_customer"].str.contains(search, case=False, na=False)
            )
            df = df[mask]
        if "product_name" in df.columns:
            df = df.sort_values("product_name", key=lambda s: s.str.casefold())

    # Standardize column names for movement log even when there are no rows,
    # so the UI shows friendly headers instead of raw DB column names.
    rename_map = {
        "product_name": "Name",
        "product_category": "Category",
        "movement_type": "Type",
        "quantity": "Quantity",
        "price": "Price",
        "supplier_customer": "Party",
        "notes": "Notes",
        "movement_date": "Date",
    }
    df = df.rename(columns=rename_map)
    # Ensure all movement columns exist
    move_cols = [
        "Name",
        "Category",
        "Type",
        "Quantity",
        "Price",
        "Party",
        "Date",
        "Notes",
    ]
    for col in move_cols:
        if col not in df.columns:
            df[col] = ""
    df = df[move_cols]
    
    # Display movement log
    st.markdown(
        "<style>td {vertical-align: middle !important;}</style>", unsafe_allow_html=True
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Owner can delete movements - add delete buttons below table
    user = get_current_user()
    if user['role'] == 'owner' and not df.empty:
        st.divider()
        st.caption("Delete a movement (stock will be adjusted automatically)")
        
        # Show compact delete buttons for each row
        for idx, row_data in enumerate(df_with_id.itertuples()):
            movement_id = df_with_id.iloc[idx]['id']
            display_row = df.iloc[idx]
            
            col1, col2 = st.columns([10, 1])
            with col1:
                movement_desc = f"{display_row.get('Name', 'N/A')} - {display_row.get('Type', 'N/A')} - Qty: {display_row.get('Quantity', 'N/A')} - {display_row.get('Date', 'N/A')}"
                st.text(movement_desc)
            with col2:
                if st.button("🗑️", key=f"del_{movement_id}"):
                    delete_movement(conn, movement_id)
                    st.success("Deleted and adjusted stock")
                    st.rerun()
