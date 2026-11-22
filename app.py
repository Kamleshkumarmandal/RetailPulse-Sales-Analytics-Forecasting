"""RetailPulse: interactive retail sales analytics and forecasting dashboard."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sales_analytics import prepare_sales_data, revenue_anomalies, sales_summary, monthly_revenue
from forecasting import forecast_monthly_revenue


ROOT = Path(__file__).parent
CURRENCY_SYMBOLS = {"INR (₹)": "₹", "USD ($)": "$", "EUR (€)": "€", "GBP (£)": "£"}


def money(value: float, symbol: str) -> str:
    return f"{symbol}{value:,.0f}"


st.set_page_config(page_title="RetailPulse | Sales Intelligence", page_icon="📈", layout="wide")
st.title("📈 RetailPulse")
st.caption("Retail sales intelligence • performance, trends, forecasting and anomaly checks")

with st.sidebar:
    st.header("Workspace")
    uploaded = st.file_uploader("Upload sales data", type=["csv", "xlsx", "xls"])
    currency_name = st.selectbox("Display currency", list(CURRENCY_SYMBOLS), index=0)
    currency = CURRENCY_SYMBOLS[currency_name]
    st.caption("Uploaded data is processed by this app; no third-party analytics or model API is called.")

try:
    if uploaded is None:
        raw_data = pd.read_csv(ROOT / "sample_data.csv")
        source_label = "Built-in sample data"
    else:
        if uploaded.name.lower().endswith(".csv"):
            raw_data = pd.read_csv(uploaded)
        else:
            raw_data = pd.read_excel(uploaded)
        source_label = uploaded.name
    sales = prepare_sales_data(raw_data)
except Exception as exc:
    st.error(f"Could not read this sales file: {exc}")
    st.info("Use a CSV or Excel file with a date column and sales/revenue, or units and unit price.")
    st.stop()

cost_estimated = bool(sales["_cost_estimated"].any()) if not sales.empty else False

with st.sidebar:
    st.divider()
    st.subheader("Filters")
    min_day = sales["order_date"].min().date()
    max_day = sales["order_date"].max().date()
    selected_dates = st.date_input(
        "Order date range",
        value=(min_day, max_day),
        min_value=min_day,
        max_value=max_day,
    )
    categories = sorted(sales["category"].unique().tolist())
    regions = sorted(sales["region"].unique().tolist())
    products = sorted(sales["product"].unique().tolist())
    selected_categories = st.multiselect("Categories", categories, default=categories)
    selected_regions = st.multiselect("Regions", regions, default=regions)
    selected_products = st.multiselect("Products", products, default=products)

filtered = sales.copy()
if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_day, end_day = selected_dates
    filtered = filtered[
        filtered["order_date"].dt.date.between(start_day, end_day)
    ]
filtered = filtered[
    filtered["category"].isin(selected_categories)
    & filtered["region"].isin(selected_regions)
    & filtered["product"].isin(selected_products)
].copy()

st.caption(f"Data source: **{source_label}** · {len(filtered):,} rows after filters")
if filtered.empty:
    st.warning("No rows match the current filters. Select a wider date range or restore a category, region or product.")
    st.stop()

if cost_estimated:
    st.info("Some cost values were missing. Profit and margin use an estimated cost of 65% of revenue for those rows.")

kpis = sales_summary(filtered)
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Revenue", money(kpis["revenue"], currency))
m2.metric("Profit", money(kpis["profit"], currency))
m3.metric("Orders", f'{kpis["orders"]:,.0f}')
m4.metric("Units sold", f'{kpis["units"]:,.0f}')
m5.metric("Avg. order value", money(kpis["average_order_value"], currency))
m6.metric("Profit margin", f'{kpis["profit_margin"]:.1f}%')

overview_tab, products_tab, forecast_tab, data_tab = st.tabs(
    ["Overview", "Products & Regions", "Forecast & Alerts", "Data"]
)

with overview_tab:
    left, right = st.columns([1.65, 1])
    monthly = monthly_revenue(filtered).rename("Revenue").reset_index().rename(columns={"order_date": "Month"})
    monthly["Month"] = monthly["Month"].dt.strftime("%Y-%m")
    with left:
        st.subheader("Monthly revenue")
        fig = px.area(monthly, x="Month", y="Revenue", markers=True, title=None)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title=f"Revenue ({currency})")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Revenue by category")
        category_totals = (
            filtered.groupby("category", as_index=False)["revenue"].sum()
            .sort_values("revenue", ascending=False)
        )
        fig = px.pie(category_totals, names="category", values="revenue", hole=0.55)
        fig.update_layout(margin=dict(l=5, r=5, t=10, b=5), legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Sales snapshot")
    by_month = filtered.assign(month=filtered["order_date"].dt.to_period("M").astype(str))
    table = by_month.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        orders=("order_id", "nunique"),
        units=("units", "sum"),
    )
    table = table.sort_values("month", ascending=False)
    table["revenue"] = table["revenue"].map(lambda x: money(x, currency))
    table["profit"] = table["profit"].map(lambda x: money(x, currency))
    st.dataframe(table, use_container_width=True, hide_index=True)

with products_tab:
    a, b = st.columns(2)
    with a:
        st.subheader("Top products by revenue")
        top_products = (
            filtered.groupby("product", as_index=False)["revenue"].sum()
            .nlargest(10, "revenue").sort_values("revenue")
        )
        fig = px.bar(top_products, x="revenue", y="product", orientation="h", text_auto=".2s")
        fig.update_layout(yaxis_title="", xaxis_title=f"Revenue ({currency})", margin=dict(l=5, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with b:
        st.subheader("Revenue by region")
        region_totals = filtered.groupby("region", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
        fig = px.bar(region_totals, x="region", y="revenue", color="region")
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title=f"Revenue ({currency})", margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    category_detail = filtered.groupby(["category", "product"], as_index=False).agg(
        revenue=("revenue", "sum"), profit=("profit", "sum"), units=("units", "sum")
    ).sort_values("revenue", ascending=False)
    st.subheader("Product performance table")
    st.dataframe(category_detail, use_container_width=True, hide_index=True)

with forecast_tab:
    st.subheader("Monthly revenue forecast")
    horizon = st.slider("Months to forecast", min_value=1, max_value=12, value=6)
    try:
        forecast = forecast_monthly_revenue(filtered, horizon=horizon)
        actual = monthly_revenue(filtered).reset_index()
        actual.columns = ["Month", "Revenue"]
        chart = go.Figure()
        chart.add_trace(go.Scatter(x=actual["Month"], y=actual["Revenue"], mode="lines+markers", name="Actual revenue"))
        chart.add_trace(go.Scatter(x=forecast["forecast_month"], y=forecast["forecast_revenue"], mode="lines+markers", name="Forecast", line=dict(dash="dash")))
        chart.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title=f"Revenue ({currency})",
            xaxis_title="Month",
            legend=dict(orientation="h", y=1.12),
        )
        st.plotly_chart(chart, use_container_width=True)
        st.caption("Forecast uses a Random Forest model trained on calendar patterns and recent monthly sales. Values are estimates, not guaranteed outcomes or confidence intervals.")
        f1, f2 = st.columns(2)
        f1.metric("Forecast total", money(float(forecast["forecast_revenue"].sum()), currency))
        f2.metric("Next month estimate", money(float(forecast["forecast_revenue"].iloc[0]), currency))
        forecast_display = forecast.copy()
        forecast_display["forecast_revenue"] = forecast_display["forecast_revenue"].map(lambda x: money(x, currency))
        st.dataframe(forecast_display, use_container_width=True, hide_index=True)
        st.download_button(
            "Download forecast CSV",
            data=forecast.to_csv(index=False).encode("utf-8"),
            file_name="retailpulse_forecast.csv",
            mime="text/csv",
        )
    except ValueError as exc:
        st.warning(str(exc))

    st.divider()
    st.subheader("Unusual monthly sales")
    anomalies = revenue_anomalies(filtered)
    flagged = anomalies[anomalies["is_anomaly"]].copy()
    if flagged.empty:
        st.success("No unusually high or low months were detected in the selected period.")
    else:
        st.warning(f"{len(flagged)} unusual month(s) detected using the 1.5× IQR rule.")
        flagged["revenue"] = flagged["revenue"].map(lambda x: money(x, currency))
        st.dataframe(flagged[["month", "revenue", "direction"]], use_container_width=True, hide_index=True)
    st.caption("Anomaly flags are statistical prompts for review, not evidence of fraud or an error.")

with data_tab:
    st.subheader("Filtered transaction data")
    st.dataframe(filtered.drop(columns=["_cost_estimated"]), use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered sales CSV",
        data=filtered.drop(columns=["_cost_estimated"]).to_csv(index=False).encode("utf-8"),
        file_name="retailpulse_filtered_sales.csv",
        mime="text/csv",
    )
    st.caption(f"Showing {len(filtered):,} rows. Original uploaded data is not modified.")
