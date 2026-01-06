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
                if st.button("🗑️", key=f"del_{movement_id}"):
                    delete_movement(conn, movement_id)
                    st.success("Deleted and adjusted stock")
                    st.rerun()
