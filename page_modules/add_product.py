"""Add/Edit product page."""
import streamlit as st
import sqlite3
from datetime import datetime
import psycopg2
from streamlit_free_text_select import st_free_text_select
from core.constants import POS_CATEGORIES
from core.services import (
    get_products,
    add_product,
    update_product,
    delete_product,
    restore_product,
    set_product_stock,
    find_product_by_name,
    record_movement,
)
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
    return bool(image_path) and image_path.startswith(("http://", "https://"))


def _category_input(df, key: str) -> str:
    """Render category input with suggestions and return normalized value."""
    existing_categories = (
        sorted(set(df["category"].dropna().unique()), key=str.casefold)
        if not df.empty and "category" in df.columns
        else sorted(POS_CATEGORIES, key=str.casefold)
    )
    category_input = st_free_text_select(
        "Category",
        existing_categories,
        key=key,
        placeholder="Type to search or add",
    )
    category_input = (category_input or "").strip()
    category_match = next(
        (c for c in existing_categories if c.lower() == category_input.lower()),
        None,
    )
    return category_match if category_match else (category_input.title() if category_input else "")


def _brand_input(df, key: str) -> str:
    """Render brand input with suggestions and return normalized value."""
    existing_brands = (
        sorted(set(df["brand"].dropna().unique()), key=str.casefold)
        if not df.empty and "brand" in df.columns
        else []
    )
    brand_input = st_free_text_select(
        "Brand",
        existing_brands,
        key=key,
        placeholder="Type to search or add",
    )
    brand_input = (brand_input or "").strip()
    brand_match = next(
        (b for b in existing_brands if b.lower() == brand_input.lower()),
        None,
    )
    return brand_match if brand_match else brand_input


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
        st.warning("\U0001F512 Admin only")
        return
    if st.session_state.get("product_deleted_success"):
        deleted_name = st.session_state.get("product_deleted_name", "Product")
        st.toast(f"Deleted '{deleted_name}'", icon="\U0001F5D1\ufe0f")
        del st.session_state["product_deleted_success"]
        del st.session_state["product_deleted_name"]
    if st.session_state.get("product_restored_success"):
        restored_name = st.session_state.get("product_restored_name", "Product")
        st.toast(f"Restored '{restored_name}'", icon="\u267B\ufe0f")
        del st.session_state["product_restored_success"]
        del st.session_state["product_restored_name"]
    st.header("\u2795 Add / Edit Product")
    df = get_products(conn)

    # Sort products alphabetically for predictability (case-insensitive)
    if not df.empty:
        df = df.sort_values("name", key=lambda s: s.str.casefold())

    # Persist mode selection across navigation
    mode = st.radio(
        "Choose option",
        [
            "\U0001F9FE Create New Product",
            "\U0001F4DD Edit Existing Product",
        ],
        horizontal=True,
        key="add_mode",
    )

    # ---------- Edit Existing Product (persistent fields) ----------
    if mode == "\U0001F4DD Edit Existing Product" and not df.empty:
        # Show update toast after rerun
        if st.session_state.get("product_updated_success"):
            updated_name = st.session_state.get("product_updated_name", "Product")
            st.toast(f"\u2705 Product '{updated_name}' updated", icon="\U0001F4BE")
            del st.session_state["product_updated_success"]
            del st.session_state["product_updated_name"]
            st.session_state.pop("update_product_busy", None)

        # Add indicator for inactive products (Owner only) and show brand/category
        user = get_current_user()
        display_to_name = {}
        product_names_display = []
        for _, product in df.iterrows():
            name = str(product.get("name", "")).strip()
            brand = str(product.get("brand", "") or "").strip()
            category = str(product.get("category", "") or "").strip()
            parts = [part for part in (name, brand, category) if part]
            display = " | ".join(parts) if parts else name
            if user["role"] == "owner" and "isactive" in df.columns:
                is_active = int(product.get("isactive", 1) or 1) == 1
                display = f"{display} {'\u2705' if is_active else '\u274C (Inactive)'}"
            product_names_display.append(display)
            display_to_name[display.lower()] = name

        selected_display = st_free_text_select(
            "Select Product",
            product_names_display,
            key="edit_selected",
            placeholder="Type to search or select",
        )
        if not selected_display:
            st.warning("Select an existing product to edit.")
            return

        # Map display name back to actual product name
        selected_key = str(selected_display).strip().lower()
        if selected_key not in display_to_name:
            st.warning("Select an existing product to edit.")
            return
        selected = display_to_name[selected_key]
        row = df[df["name"] == selected].iloc[0]

        # When selected product changes (or first load), initialize/edit fields from DB
        edit_missing = any(
            key not in st.session_state
            for key in [
                "edit_name",
                "edit_category",
                "edit_brand",
                "edit_cost",
                "edit_sale",
                "edit_desc",
                "edit_image",
            ]
        )
        if st.session_state.get("edit_selected_prev") != selected or edit_missing:
            product = df[df["name"] == selected].iloc[0]
            st.session_state["edit_selected_prev"] = selected
            st.session_state["edit_name"] = product["name"]
            st.session_state["edit_category"] = product["category"]
            st.session_state["edit_brand"] = product.get("brand", "")
            st.session_state["edit_cost"] = float(product["cost_price"])
            st.session_state["edit_sale"] = float(product["sale_price"])
            st.session_state["edit_desc"] = product["description"]
            st.session_state["edit_image"] = product["image_url"]

        edit_name = st.text_input("Product Name *", key="edit_name")
        # Category input with suggestions from existing products
        category = _category_input(df, "edit_category")
        if not category:
            st.caption("Category is required. Use 'Other' if needed.")

        # Brand input with live suggestions and deduplication
        brand = _brand_input(df, "edit_brand")
        if not brand:
            st.caption("Brand is required. Use 'Other' if needed.")
        
        supplier = row.get("supplier", "")
        
        # When keys are set in `st.session_state` (above) avoid passing an
        # explicit `value=` to the widget -- Streamlit warns if a widget is
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
            def _is_nan(value) -> bool:
                return isinstance(value, float) and value != value

            def _text_or_empty(value) -> str:
                if value is None or _is_nan(value):
                    return ""
                return str(value)

            def _num_or_zero(value) -> float:
                if value is None or _is_nan(value):
                    return 0.0
                return float(value)

            original_name = _text_or_empty(row.get("name", ""))
            original_category = _text_or_empty(row.get("category", ""))
            original_brand = _text_or_empty(row.get("brand", ""))
            original_desc = _text_or_empty(row.get("description", ""))
            original_image = _text_or_empty(row.get("image_url", ""))
            original_cost = _num_or_zero(row.get("cost_price", 0.0))
            original_sale = _num_or_zero(row.get("sale_price", 0.0))

            edit_dirty = any(
                [
                    (edit_name or "").strip() != original_name.strip(),
                    (category or "").strip() != original_category.strip(),
                    (brand or "").strip() != original_brand.strip(),
                    (desc or "").strip() != original_desc.strip(),
                    (image or "").strip() != original_image.strip(),
                    float(cost) != original_cost,
                    float(sale) != original_sale,
                ]
            )

            update_btn_disabled = not edit_name or not category or not brand or not edit_dirty
            update_busy = st.session_state.get("update_product_busy", False)
            if st.button(
                "\U0001F4BE Update Product",
                width="stretch",
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
                        f"\u274C Product '{edit_name or selected}' already exists.",
                        icon="\u26A0\ufe0f",
                    )
                except Exception as e:
                    st.toast(f"\u274C Could not update product: {e}", icon="\u26A0\ufe0f")
                else:
                    st.session_state["product_updated_success"] = True
                    st.session_state["product_updated_name"] = edit_name or selected
                    # Reset edit fields to default values on next run
                    for key in [
                        "edit_name",
                        "edit_category",
                        "edit_brand",
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
                    if st.button("\U0001F5D1\ufe0f Delete", width="stretch"):
                        delete_product(conn, selected)
                        st.session_state["product_deleted_success"] = True
                        st.session_state["product_deleted_name"] = selected
                        st.rerun()
                else:
                    if st.button("\u267B\ufe0f Restore", width="stretch"):
                        restore_product(conn, selected)
                        st.session_state["product_restored_success"] = True
                        st.session_state["product_restored_name"] = selected
                        st.rerun()

    # ---------- Create New Product (persistent fields) ----------
    else:
        if st.session_state.pop("reset_add_form", False):
            st.session_state["add_name"] = ""
            st.session_state["add_category"] = ""
            st.session_state["add_brand"] = ""
            st.session_state["add_cost"] = 0.0
            st.session_state["add_sale"] = 0.0
            st.session_state["add_stock"] = 0
            st.session_state["add_desc"] = ""
            st.session_state["add_image"] = ""
        # Check if we just added a product successfully
        if st.session_state.get("product_added_success"):
            product_name = st.session_state.get("product_added_name", "Product")
            st.toast(f"\u2705 Product '{product_name}' added", icon="\u2705")
            del st.session_state["product_added_success"]
            del st.session_state["product_added_name"]
            st.session_state.pop("add_product_busy", None)

        existing_names = (
            df["name"].dropna().astype(str).tolist()
            if not df.empty and "name" in df.columns
            else []
        )
        name = st_free_text_select(
            "Product Name *",
            existing_names,
            key="add_name",
            placeholder="Type to search or add",
        )
        name = (name or "").strip()
        inactive_match = None
        active_exists = False
        active_names = set()
        if not df.empty and "name" in df.columns:
            active_names = {
                n.strip().casefold()
                for n in df["name"].dropna().astype(str).tolist()
                if str(n).strip()
            }
        if name:
            normalized = name.strip().casefold()
            if normalized in active_names:
                active_exists = True
            else:
                match = find_product_by_name(conn, name)
                if match:
                    inactive_match = match
        # Category input with suggestions from existing products
        category = _category_input(df, "add_category")
        if not category:
            st.caption("Category is required. Use 'Other' if needed.")

        # Brand input with live suggestions and deduplication
        brand = _brand_input(df, "add_brand")
        if not brand:
            st.caption("Brand is required. Use 'Other' if needed.")
        
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
        if not image or not _is_external_url(image):
            local_image = _resolve_local_image(name)
            if local_image:
                image = local_image
        # Disable add button if required fields are missing
        add_btn_disabled = (
            not name
            or not category
            or not brand
            or cost is None
            or sale is None
            or stock is None
            or inactive_match is not None
            or active_exists
        )
        add_busy = st.session_state.get("add_product_busy", False)
        if inactive_match is not None:
            st.warning("A product with this name exists but is inactive.")
            if st.button("\u267B\ufe0f Restore and Update", disabled=add_busy):
                st.session_state["add_product_busy"] = True
                try:
                    restore_product(conn, inactive_match["name"])
                    update_product(
                        conn,
                        (
                            name,
                            category,
                            brand,
                            desc,
                            image,
                            float(cost),
                            float(sale),
                            "",  # Empty supplier - will be filled when recording movements
                            inactive_match["name"],
                        ),
                    )
                    set_product_stock(conn, name, int(stock))
                except Exception as e:
                    st.toast(f"\u274C Could not restore product: {e}", icon="\u26A0\ufe0f")
                else:
                    st.session_state["product_added_success"] = True
                    st.session_state["product_added_name"] = name
                    st.session_state["reset_add_form"] = True
                    st.session_state["add_product_busy"] = False
                    st.rerun()
                st.session_state["add_product_busy"] = False
        elif active_exists:
            st.error("A product with this name already exists.")
        if st.button("\u2705 Add Product", disabled=add_btn_disabled or add_busy):
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
                        0,  # Track initial stock via movement log
                        float(cost),
                        float(sale),
                        "",  # Empty supplier - will be filled when recording movements
                    ),
                )
                if int(stock) > 0:
                    record_movement(
                        conn,
                        (
                            name,
                            category,
                            "INITIAL STOCK",
                            int(stock),
                            float(cost) if cost is not None else "N/A",
                            "",
                            "Auto-created on product add",
                            datetime.now().date(),
                        ),
                    )
            except (sqlite3.IntegrityError, psycopg2.IntegrityError):
                st.toast(f"\u274C Product '{name}' already exists.", icon="\u26A0\ufe0f")
            except Exception as e:
                st.toast(f"\u274C Could not add product: {e}", icon="\u26A0\ufe0f")
            else:
                # Set flag to show success toast and reset on next run
                st.session_state["product_added_success"] = True
                st.session_state["product_added_name"] = name
                st.session_state["reset_add_form"] = True
                st.session_state["add_product_busy"] = False
                st.rerun()
            st.session_state["add_product_busy"] = False
