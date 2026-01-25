"""Movement log page to view transaction history."""
import streamlit as st
from core.constants import MOVEMENT_TYPES
from core.services import get_movements, delete_movement
from core.simple_auth import get_current_user


def render(conn):
    """Render the movement log page."""
    st.header("\U0001F501 Movement Log")
    if st.session_state.get("movement_deleted_success"):
        msg = st.session_state.get("movement_deleted_msg", "Movement deleted")
        st.toast(msg, icon="\U0001F5D1\ufe0f")
        del st.session_state["movement_deleted_success"]
        del st.session_state["movement_deleted_msg"]
    days = st.selectbox("Last", [1, 7, 30, 90, "All"])
    movement_filter_types = MOVEMENT_TYPES + ["INITIAL STOCK"]
    types = st.multiselect("Type", movement_filter_types, default=movement_filter_types)
    days_val = None if days == "All" else days
    if not types:
        df = get_movements(conn, days_val, None).iloc[0:0]
    else:
        df = get_movements(conn, days_val, types)
    
    search = st.text_input("Search by name, category, or party")
    if not df.empty:
        # Case-insensitive partial search across product_name, product_category, party
        if search:
            mask = None
            if "product_name" in df.columns:
                mask = df["product_name"].str.contains(search, case=False, na=False, regex=False)
            if "product_category" in df.columns:
                col_mask = df["product_category"].str.contains(search, case=False, na=False, regex=False)
                mask = col_mask if mask is None else (mask | col_mask)
            if "supplier_customer" in df.columns:
                col_mask = df["supplier_customer"].str.contains(search, case=False, na=False, regex=False)
                mask = col_mask if mask is None else (mask | col_mask)
            if mask is not None:
                df = df[mask]
        if "product_name" in df.columns:
            df = df.sort_values("product_name", key=lambda s: s.str.casefold())

    # Keep ID column before renaming (for delete functionality)
    df_display = df.copy()
    
    # Add +/- to quantity based on movement type for better clarity
    if not df_display.empty and 'quantity' in df_display.columns and 'movement_type' in df_display.columns:
        def format_quantity(row):
            qty = row['quantity']
            mov_type = row['movement_type']
            if mov_type in ['PURCHASE', 'RECEIVED']:
                return f"+{qty}"
            elif mov_type in ['SALE', 'ISSUED']:
                return f"-{qty}"
            else:  # ADJUSTMENT
                return f"+{qty}" if qty >= 0 else str(qty)
        
        df_display['quantity'] = df_display.apply(format_quantity, axis=1)
    
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
    df_display = df_display.rename(columns=rename_map)
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
        if col not in df_display.columns:
            df_display[col] = ""
    df_display = df_display[move_cols]
    
    # Display movement log (left-aligned by default)
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    # Owner can delete movements - add delete buttons below table
    user = get_current_user()
    if user['role'] == 'owner' and not df.empty:
        st.divider()
        st.caption("Delete a movement (stock will be adjusted automatically)")
        
        # Show compact delete buttons for each row (using original df with ID)
        for idx in range(len(df)):
            movement_id = df.iloc[idx]['id']
            movement_name = df.iloc[idx].get('product_name', 'N/A')
            movement_type = df.iloc[idx].get('movement_type', 'N/A')
            movement_qty = df.iloc[idx].get('quantity', 'N/A')
            movement_date = df.iloc[idx].get('movement_date', 'N/A')
            
            col1, col2 = st.columns([10, 1])
            with col1:
                movement_desc = f"{movement_name} - {movement_type} - Qty: {movement_qty} - {movement_date}"
                st.text(movement_desc)
            with col2:
                if st.button("\U0001F5D1\ufe0f", key=f"del_{movement_id}_{idx}"):
                    try:
                        delete_movement(conn, int(movement_id))
                    except Exception as e:
                        st.toast(f"\u274C Delete failed: {e}", icon="\u26A0\ufe0f")
                    else:
                        st.session_state["movement_deleted_success"] = True
                        st.session_state["movement_deleted_msg"] = "Deleted and adjusted stock"
                        st.rerun()
