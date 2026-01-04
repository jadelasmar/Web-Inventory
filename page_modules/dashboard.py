"""Dashboard page with inventory overview and statistics."""
import streamlit as st
import pandas as pd
import plotly.express as px
from core.services import get_products, get_movements


def render(conn):
    """Render the dashboard page."""
    st.header("📊 Inventory Overview")
    df = get_products(conn)
    if df.empty:
        st.info("No products available")
        return

    # Sort products alphabetically for consistent display (case-insensitive)
    df = df.sort_values("name", key=lambda s: s.str.casefold())

    # Calculate core metrics
    total_cost = (df["current_stock"] * df["cost_price"]).sum()
    sale_total = (df["current_stock"] * df["sale_price"]).sum()
    profit_potential = sale_total - total_cost

    # Row 1: Core metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Products", len(df))
    col2.metric("Total Items", int(df["current_stock"].sum()))
    col3.metric("Total Cost", f"${total_cost:,.2f}")
    col4.metric("Profit Potential", f"${profit_potential:,.2f}")

    # Row 2: Value metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Inventory Value (Retail)", f"${sale_total:,.2f}")

    # Average profit margin %
    if len(df) > 0:
        avg_margin = (
            ((df["sale_price"] - df["cost_price"]) / df["cost_price"]) * 100
        ).mean()
        col2.metric("Avg Profit Margin", f"{avg_margin:.1f}%")
    else:
        col2.metric("Avg Profit Margin", "N/A")

    # Total suppliers (from products + movements)
    suppliers_from_products = set(df["supplier"].dropna().unique())
    movements_df = get_movements(conn, days=None, types=["PURCHASE"])
    if not movements_df.empty:
        suppliers_from_movements = set(
            movements_df["supplier_customer"].dropna().unique()
        )
        total_suppliers = suppliers_from_products | suppliers_from_movements
    else:
        total_suppliers = suppliers_from_products
    col3.metric("Total Suppliers", len(total_suppliers))

    # Total customers (from sales movements)
    customer_movements = get_movements(conn, days=None, types=["SALE"])
    if not customer_movements.empty:
        customers = set(customer_movements["supplier_customer"].dropna().unique())
        col4.metric("Total Customers", len(customers))
    else:
        col4.metric("Total Customers", 0)

    # Row 3: Product insights
    col1, col2, col3, col4 = st.columns(4)

    # Best value product
    df["total_value"] = df["current_stock"] * df["sale_price"]
    if len(df) > 0:
        best_product = df.loc[df["total_value"].idxmax()]
        col1.metric(
            "Best Value Product",
            best_product["name"][:20],
            f"${best_product['total_value']:,.0f}",
        )
    else:
        col1.metric("Best Value Product", "N/A")

    # Average product value
    avg_value = df["total_value"].mean()
    col2.metric("Avg Product Value", f"${avg_value:,.2f}")

    # Low stock items (threshold: 5)
    low_stock_count = len(df[df["current_stock"] <= 5])
    col3.metric("Low Stock Items", low_stock_count)

    # Out of stock items
    out_of_stock = len(df[df["current_stock"] == 0])
    col4.metric("Out of Stock", out_of_stock)

    # Visual sections
    st.markdown("---")

    # Stock distribution by category (Pie chart)
    st.subheader("📊 Stock Distribution by Category")
    category_stock = df.groupby("category")["current_stock"].sum().reset_index()
    category_stock = category_stock[category_stock["current_stock"] > 0]
    category_stock = category_stock.sort_values("current_stock", ascending=False)

    # Show top 10 categories, group rest as "Other"
    if len(category_stock) > 10:
        top_10 = category_stock.head(10)
        other_sum = category_stock.tail(len(category_stock) - 10)["current_stock"].sum()
        if other_sum > 0:
            other_row = pd.DataFrame(
                {"category": ["Other"], "current_stock": [other_sum]}
            )
            category_stock = pd.concat([top_10, other_row], ignore_index=True)
        else:
            category_stock = top_10

    if not category_stock.empty:
        # 10 colors: Your 6 rainbow colors + 4 additional vibrant colors
        colors = [
            "#F54F52",
            "#93F03B",
            "#378AFF",
            "#FFEC21",
            "#9552EA",
            "#FFA32F",
            "#00CED1",
            "#FF1493",
            "#20B2AA",
            "#FF00FF",
        ]

        fig = px.pie(
            category_stock,
            values="current_stock",
            names="category",
            title="Stock by Category (Top 10)",
            color_discrete_sequence=colors,
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("No stock data to display")

    # Top 10 products by value (Bar chart)
    st.subheader("💰 Top 10 Products by Inventory Value")
    top_10 = df.nlargest(10, "total_value")[["name", "total_value"]]

    if not top_10.empty:
        fig = px.bar(
            top_10,
            x="name",
            y="total_value",
            title="Top 10 Products by Value",
            labels={"name": "Product", "total_value": "Value ($)"},
            color="total_value",
            color_continuous_scale="Viridis",
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("No products to display")

    # Recent activity (Last 5 movements)
    st.subheader("🔄 Recent Activity")
    recent_movements = get_movements(conn, days=7, types=None)

    if not recent_movements.empty:
        recent_movements = recent_movements.head(5)
        display_cols = [
            "product_name",
            "movement_type",
            "quantity",
            "supplier_customer",
            "movement_date",
        ]
        recent_movements = recent_movements[display_cols].rename(
            columns={
                "product_name": "Product",
                "movement_type": "Type",
                "quantity": "Qty",
                "supplier_customer": "Party",
                "movement_date": "Date",
            }
        )
        st.dataframe(recent_movements, width='stretch', hide_index=True)
    else:
        st.info("No recent activity")
