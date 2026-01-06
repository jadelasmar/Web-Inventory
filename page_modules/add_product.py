"""Add/Edit product page."""
import streamlit as st
import sqlite3
from core.constants import POS_CATEGORIES
from core.services import get_products, add_product, update_product, delete_product, restore_product
from core.simple_auth import get_current_user


def render(conn):
    """Render the add/edit product page."""
    if not st.session_state.admin_mode:
        st.warning("🔒 Admin only")
        return
    st.header("➕ Add / Edit Product")
    df = get_products(conn)

    # Sort products alphabetically for predictability (case-insensitive)
    if not df.empty:
        df = df.sort_values("name", key=lambda s: s.str.casefold())

    # Persist mode selection across navigation
    mode = st.radio(
        "Choose option",
        [
            "➕ Create New Product",
            "📝 Edit Existing Product",
        ],
        horizontal=True,
        key="add_mode",
    )

    # ---------- Edit Existing Product (persistent fields) ----------
    if mode == "📝 Edit Existing Product" and not df.empty:
        # Add indicator for inactive products (Owner only)
        user = get_current_user()
        product_names = df["name"].tolist()
        if user['role'] == 'owner' and "isactive" in df.columns:
            product_names = [
                f"{name} {'✅' if df[df['name']==name].iloc[0]['isactive']==1 else '❌ (Inactive)'}"
                for name in df["name"]
            ]
        
        selected_display = st.selectbox(
            "Select Product",
            product_names,
            key="edit_selected",
        )
        # Extract actual product name (remove status indicator)
        selected = selected_display.split(" ")[0] if user['role'] == 'owner' else selected_display

        # When selected product changes, initialize/edit fields from DB
        if st.session_state.get("edit_selected_prev") != selected:
            product = df[df["name"] == selected].iloc[0]
            st.session_state["edit_selected_prev"] = selected
            st.session_state["edit_category"] = product["category"]
            st.session_state["edit_supplier"] = product["supplier"]
            st.session_state["edit_cost"] = float(product["cost_price"])
            st.session_state["edit_sale"] = float(product["sale_price"])
            st.session_state["edit_desc"] = product["description"]
            st.session_state["edit_image"] = product["image_url"]

        # Category input with suggestions from existing products
        existing_categories = (
            sorted(set(df["category"].dropna().unique()), key=str.casefold)
            if not df.empty and "category" in df.columns
            else sorted(POS_CATEGORIES, key=str.casefold)
        )
        category_input = st.text_input("Category", key="edit_category")
        category_match = next(
            (
                c
                for c in existing_categories
                if c.lower() == (category_input or "").lower()
            ),
            None,
        )
        category_suggestions = [
            c
            for c in existing_categories
            if category_input and category_input.lower() in c.lower()
        ]
        if category_input:
            if category_match:
                st.info(f"Using existing category: {category_match}")
            else:
                st.info("This will be a new category.")
            if category_suggestions and not category_match:
                st.write("Suggestions:")
                st.write(", ".join(category_suggestions))
        category = category_match if category_match else (category_input.title() if category_input else "")
        
        # Supplier input with live suggestions and deduplication (same as Create mode)
        existing_suppliers = (
            sorted(set(df["supplier"].dropna().unique()), key=str.casefold)
            if not df.empty and "supplier" in df.columns
            else []
        )
        supplier_input = st.text_input("Supplier", key="edit_supplier")
        supplier_match = next(
            (
                s
                for s in existing_suppliers
                if s.lower() == (supplier_input or "").lower()
            ),
            None,
        )
        supplier_suggestions = [
            s
            for s in existing_suppliers
            if supplier_input and supplier_input.lower() in s.lower()
        ]
        if supplier_input:
            if supplier_match:
                st.info(f"Will use existing supplier: {supplier_match}")
            else:
                st.info("This will be a new supplier.")
            if supplier_suggestions and not supplier_match:
                st.write("Suggestions:")
                st.write(", ".join(supplier_suggestions))
        supplier = supplier_match if supplier_match else supplier_input
        
        # When keys are set in `st.session_state` (above) avoid passing an
        # explicit `value=` to the widget — Streamlit warns if a widget is
        # created with both a default value and a session-state value.
        cost = st.number_input("Cost", key="edit_cost")
        sale = st.number_input("Price", key="edit_sale")
        desc = st.text_area("Description", key="edit_desc")
        image = st.text_input("Image URL", key="edit_image")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("💾 Update Product", use_container_width=True):
                update_product(
                    conn,
                    (
                        category,
                        desc,
                        image,
                        float(cost),
                        float(sale),
                        supplier,
                        selected,
                    ),
                )
                msg = f"✅ Product '{selected}' updated"
                st.toast(msg, icon="💾")
        
        # Owner-only: Delete/Restore product
        with col2:
            user = get_current_user()
            if user['role'] == 'owner':
                product = df[df["name"] == selected].iloc[0]
                is_active = product.get("isactive", 1) == 1
                
                if is_active:
                    if st.button("🗑️ Delete", use_container_width=True):
                        delete_product(conn, selected)
                        st.success(f"Deleted '{selected}'")
                        st.rerun()
                else:
                    if st.button("♻️ Restore", use_container_width=True):
                        restore_product(conn, selected)
                        st.success(f"Restored '{selected}'")
                        st.rerun()

    # ---------- Create New Product (persistent fields) ----------
    else:
        # Check if we just added a product successfully
        if st.session_state.get("product_added_success"):
            product_name = st.session_state.get("product_added_name", "Product")
            st.toast(f"✅ Product '{product_name}' added", icon="➕")
            del st.session_state["product_added_success"]
            del st.session_state["product_added_name"]

        name = st.text_input("Product Name *", key="add_name")
        # Category input with suggestions from existing products
        existing_categories = (
            sorted(set(df["category"].dropna().unique()), key=str.casefold)
            if not df.empty and "category" in df.columns
            else sorted(POS_CATEGORIES, key=str.casefold)
        )
        category_input = st.text_input("Category", key="add_category")
        category_match = next(
            (
                c
                for c in existing_categories
                if c.lower() == (category_input or "").lower()
            ),
            None,
        )
        category_suggestions = [
            c
            for c in existing_categories
            if category_input and category_input.lower() in c.lower()
        ]
        if category_input:
            if category_match:
                st.info(f"Using existing category: {category_match}")
            else:
                st.info("This will be a new category.")
            if category_suggestions and not category_match:
                st.write("Suggestions:")
                st.write(", ".join(category_suggestions))
        category = category_match if category_match else (category_input.title() if category_input else "")
        # Streamlined supplier field: text input with live suggestions and deduplication
        existing_suppliers = (
            sorted(set(df["supplier"].dropna().unique()), key=str.casefold)
            if not df.empty and "supplier" in df.columns
            else []
        )
        supplier_input = st.text_input("Supplier", key="add_supplier")
        match = next(
            (
                s
                for s in existing_suppliers
                if s.lower() == (supplier_input or "").lower()
            ),
            None,
        )
        suggestions = [
            s
            for s in existing_suppliers
            if supplier_input and supplier_input.lower() in s.lower()
        ]
        if supplier_input:
            if match:
                st.info(f"Will use existing supplier: {match}")
            else:
                st.info("This will be a new supplier.")
            if suggestions and not match:
                st.write("Suggestions:")
                st.write(", ".join(suggestions))
        # Add stock input for new product
        stock = st.number_input("Stock", min_value=0, key="add_stock")
        cost = st.number_input(
            "Cost",
            key="add_cost",
        )
        sale = st.number_input(
            "Price",
            key="add_sale",
        )
        desc = st.text_area("Description", key="add_desc")
        image = st.text_input("Image URL", key="add_image")
        # Disable add button if required fields are missing
        add_btn_disabled = not name or cost is None or sale is None or stock is None
        if st.button("➕ Add Product", disabled=add_btn_disabled):
            if not supplier_input:
                st.toast("Please enter a supplier name.", icon="⚠️")
                return
            supplier_to_use = match if match else supplier_input.title()
            try:
                add_product(
                    conn,
                    (
                        name,
                        category,
                        desc,
                        image,
                        int(stock),
                        float(cost),
                        float(sale),
                        supplier_to_use,
                    ),
                )
            except sqlite3.IntegrityError:
                st.toast(f"❌ Product '{name}' already exists.", icon="⚠️")
            except Exception as e:
                st.toast(f"❌ Could not add product: {e}", icon="⚠️")
            else:
                # Set flag to show success toast on next run
                st.session_state["product_added_success"] = True
                st.session_state["product_added_name"] = name
                # clear form values but keep category selection
                for k in [
                    "add_name",
                    "add_category",
                    "add_supplier",
                    "add_cost",
                    "add_sale",
                    "add_stock",
                    "add_desc",
                    "add_image",
                ]:
                    st.session_state.pop(k, None)
                st.rerun()
