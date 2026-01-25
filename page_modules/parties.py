"""Parties management page (suppliers/customers)."""
import streamlit as st

from core.constants import PARTY_TYPES
from core.services import get_parties, upsert_party, update_party_name, deactivate_party
from streamlit_free_text_select import st_free_text_select
from core.simple_auth import get_current_user


def render(conn):
    """Render parties management page."""
    user = get_current_user()
    if user["role"] not in ["admin", "owner"]:
        st.error("\u26D4 Access denied. This page is for admins and owners only.")
        return

    st.title("\U0001F465 Customers & Suppliers")
    st.caption("Manage suppliers and customers used in movements.")

    st.subheader("Add party")
    with st.form("add_party_form", clear_on_submit=True):
        new_name = st.text_input("Name")
        new_type = st.selectbox("Type", PARTY_TYPES, index=0)
        submitted = st.form_submit_button("\u2705 Add party")
        if submitted:
            if not new_name.strip():
                st.error("Name is required.")
            else:
                try:
                    upsert_party(conn, new_name.strip(), new_type)
                    st.success("Party saved.")
                except Exception as e:
                    st.error(f"Failed to add party: {e}")

    st.subheader("Existing parties")
    parties_df = get_parties(conn, include_inactive=False)
    if parties_df.empty:
        st.info("No parties found.")
        return

    parties_df = parties_df.sort_values("name", key=lambda s: s.str.casefold())
    party_options = parties_df["name"].tolist()
    selected_party = st_free_text_select(
        "Select party",
        party_options,
        key="party_select",
        placeholder="Type to search or select",
    )
    if not selected_party or selected_party not in party_options:
        st.warning("Select an existing party to edit.")
        return

    row = parties_df[parties_df["name"] == selected_party].iloc[0]
    with st.container():
        col1, col2, col3 = st.columns([4, 3, 1])
        with col1:
            st.write(f"**{row['name']}**")
            st.caption(f"Type: {row.get('party_type', 'Other')}")
        with col2:
            new_label = st.text_input(
                "Rename",
                value=row["name"],
                key=f"party_rename_{row['id']}",
            )
            if new_label.strip() and new_label.strip() != row["name"]:
                if st.button("\U0001F4BE Save", key=f"party_save_{row['id']}"):
                    try:
                        update_party_name(conn, row["name"], new_label.strip())
                        st.success("Renamed.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Rename failed: {e}")
        with col3:
            if st.button("\U0001F5D1\ufe0f Delete", key=f"party_del_{row['id']}"):
                try:
                    deactivate_party(conn, row["name"])
                    st.success("Deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")
        st.divider()
