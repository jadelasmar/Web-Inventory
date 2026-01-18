"""Add/Edit product page."""
import streamlit as st
import sqlite3
import psycopg2
from core.constants import POS_CATEGORIES
from core.services import get_products, add_product, update_product, delete_product, restore_product
from core.simple_auth import get_current_user
from pathlib import Path


def _resolve_local_image(product_name: str) -> str:
    """Return a local image path for a product name if a file exists."""
    image_dir = Path("assets/product_images")
    for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
        candidate = image_dir / f"{product_name}{ext}"
        if candidate.exists():
            return str(candidate)
    return ""


def _is_external_url(image_path: str) -> bool:
    return image_path.startswith(("http://", "https://"))


def _maybe_rename_local_image(old_name: str, new_name: str, image_path: str) -> str:
    """Rename local image file when product name changes and update the path."""
    if not image_path or _is_external_url(image_path) or old_name == new_name:
        return image_path

    image_path_obj = Path(image_path)
    suffix = image_path_obj.suffix
    if not suffix:
        local_existing = _resolve_local_image(old_name)
        suffix = Path(local_existing).suffix if local_existing else ""

    candidates = []
    if image_path_obj.exists():
        candidates.append(image_path_obj)
    if suffix:
        candidates.append(Path("assets/product_images") / f"{old_name}{suffix}")
    else:
        local_existing = _resolve_local_image(old_name)
        if local_existing:
            candidates.append(Path(local_existing))
            suffix = Path(local_existing).suffix

    current = next((p for p in candidates if p.exists()), None)
    if current and suffix:
        target = Path("assets/product_images") / f"{new_name}{suffix}"
        if current.resolve() != target.resolve():
            try:
                if not target.exists():
                    current.rename(target)
            except Exception:
                return image_path
        if target.exists():
            return str(target)

    return image_path


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
            "🧾 Create New Product",
            "📝 Edit Existing Product",
        ],
        horizontal=True,
        key="add_mode",
    )

    # ---------- Edit Existing Product (persistent fields) ----------
    if mode == "📝 Edit Existing Product" and not df.empty:
        # Show update toast after rerun
        if st.session_state.get("product_updated_success"):
            updated_name = st.session_state.get("product_updated_name", "Product")
            st.toast(f"✅ Product '{updated_name}' updated", icon="💾")
            del st.session_state["product_updated_success"]
            del st.session_state["product_updated_name"]

        # Add indicator for inactive products (Owner only)
        user = get_current_user()
        product_names_original = df["name"].tolist()
        product_names_display = product_names_original.copy()
        
        if user['role'] == 'owner' and "isactive" in df.columns:
            product_names_display = [
                f"{name} {'✅' if df[df['name']==name].iloc[0]['isactive']==1 else '❌ (Inactive)'}"
                for name in product_names_original
            ]
        
        selected_display = st.selectbox(
            "Select Product",
            product_names_display,
            key="edit_selected",
        )
        
        # Map display name back to actual product name
        selected_index = product_names_display.index(selected_display)
        selected = product_names_original[selected_index]

        # When selected product changes, initialize/edit fields from DB
        if st.session_state.get("edit_selected_prev") != selected:
            product = df[df["name"] == selected].iloc[0]
            st.session_state["edit_selected_prev"] = selected
            st.session_state["edit_name"] = product["name"]
            st.session_state["edit_category"] = product["category"]
            st.session_state["edit_brand"] = product.get("brand", "")
            st.session_state["edit_supplier"] = product["supplier"]
            st.session_state["edit_cost"] = float(product["cost_price"])
            st.session_state["edit_sale"] = float(product["sale_price"])
            st.session_state["edit_desc"] = product["description"]
            st.session_state["edit_image"] = product["image_url"]

        edit_name = st.text_input("Product Name *", key="edit_name")
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

        # Brand input with live suggestions and deduplication
        existing_brands = (
            sorted(set(df["brand"].dropna().unique()), key=str.casefold)
            if not df.empty and "brand" in df.columns
            else []
        )
        brand_input = st.text_input("Brand", key="edit_brand")
        brand_match = next(
            (
                b
                for b in existing_brands
                if b.lower() == (brand_input or "").lower()
            ),
            None,
        )
        brand_suggestions = [
            b
            for b in existing_brands
            if brand_input and brand_input.lower() in b.lower()
        ]
        if brand_input:
            if brand_match:
                st.info(f"Will use existing brand: {brand_match}")
            else:
                st.info("This will be a new brand.")
            if brand_suggestions and not brand_match:
                st.write("Suggestions:")
                st.write(", ".join(brand_suggestions))
        brand = brand_match if brand_match else brand_input
        
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
        # Auto-assign image if field is empty or local path; keep external URLs intact.
        if not image or not _is_external_url(image):
            target_name = edit_name or selected
            source_image = image
            if target_name != selected:
                if not source_image:
                    source_image = _resolve_local_image(selected)
                if source_image and not _is_external_url(source_image):
                    image = _maybe_rename_local_image(selected, target_name, source_image)
            local_image = _resolve_local_image(target_name)
            if local_image:
                image = local_image
        
        col1, col2 = st.columns([3, 1])
        with col1:
            update_btn_disabled = not edit_name
            update_busy = st.session_state.get("update_product_busy", False)
            if st.button(
                "💾 Update Product",
                use_container_width=True,
                disabled=update_btn_disabled or update_busy,
            ):
                st.session_state["update_product_busy"] = True
                try:
                    update_product(
                        conn,
                        (
                            edit_name,
                            category,
                            brand,
                            desc,
                            image,
                            float(cost),
                            float(sale),
                            supplier,
                            selected,
                        ),
                    )
                except (sqlite3.IntegrityError, psycopg2.IntegrityError):
                    st.toast(
                        f"❌ Product '{edit_name or selected}' already exists.",
                        icon="⚠️",
                    )
                except Exception as e:
                    st.toast(f"❌ Could not update product: {e}", icon="⚠️")
                else:
                    st.session_state["product_updated_success"] = True
                    st.session_state["product_updated_name"] = edit_name or selected
                    # Reset edit fields to default values on next run
                    for key in [
                        "edit_name",
                        "edit_category",
                        "edit_brand",
                        "edit_supplier",
                        "edit_cost",
                        "edit_sale",
                        "edit_desc",
                        "edit_image",
                        "edit_selected_prev",
                    ]:
                        st.session_state.pop(key, None)
                    st.session_state["update_product_busy"] = False
                    st.rerun()
                st.session_state["update_product_busy"] = False
        
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
            st.toast(f"✅ Product '{product_name}' added", icon="✅")
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

        # Brand input with live suggestions and deduplication
        existing_brands = (
            sorted(set(df["brand"].dropna().unique()), key=str.casefold)
            if not df.empty and "brand" in df.columns
            else []
        )
        brand_input = st.text_input("Brand", key="add_brand")
        brand_match = next(
            (
                b
                for b in existing_brands
                if b.lower() == (brand_input or "").lower()
            ),
            None,
        )
        brand_suggestions = [
            b
            for b in existing_brands
            if brand_input and brand_input.lower() in b.lower()
        ]
        if brand_input:
            if brand_match:
                st.info(f"Will use existing brand: {brand_match}")
            else:
                st.info("This will be a new brand.")
            if brand_suggestions and not brand_match:
                st.write("Suggestions:")
                st.write(", ".join(brand_suggestions))
        brand = brand_match if brand_match else brand_input
        
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
        # Auto-assign image if field is empty or local path and file exists in assets/product_images
        if not image or not image.startswith(("http://", "https://")):
            local_image = _resolve_local_image(name)
            if local_image:
                image = local_image
        # Disable add button if required fields are missing
        add_btn_disabled = not name or cost is None or sale is None or stock is None
        add_busy = st.session_state.get("add_product_busy", False)
        if st.button("✅ Add Product", disabled=add_btn_disabled or add_busy):
            st.session_state["add_product_busy"] = True
            try:
                add_product(
                    conn,
                    (
                        name,
                        category,
                        brand,
                        desc,
                        image,
                        int(stock),
                        float(cost),
                        float(sale),
                        "",  # Empty supplier - will be filled when recording movements
                    ),
                )
            except (sqlite3.IntegrityError, psycopg2.IntegrityError):
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
                    "add_brand",
                    "add_cost",
                    "add_sale",
                    "add_stock",
                    "add_desc",
                    "add_image",
                ]:
                    st.session_state.pop(k, None)
                st.session_state["add_product_busy"] = False
                st.rerun()
            st.session_state["add_product_busy"] = False
