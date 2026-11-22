"""Data preparation and sales KPI helpers for RetailPulse."""
from __future__ import annotations

import re
import numpy as np
import pandas as pd


ALIASES = {
    "order_date": ["date", "orderdate", "transaction_date", "invoice_date", "sales_date"],
    "revenue": ["sales", "amount", "total_sales", "net_sales", "sales_amount"],
    "units": ["quantity", "qty", "units_sold"],
    "unit_price": ["price", "selling_price", "price_per_unit"],
    "cost": ["total_cost", "cogs", "cost_of_goods_sold"],
    "profit": ["gross_profit", "net_profit"],
    "order_id": ["order", "invoice", "invoice_id", "transaction_id"],
    "product": ["item", "product_name", "sku"],
    "category": ["product_category", "department"],
    "region": ["market", "area", "sales_region"],
}


def _normalise_name(name: object) -> str:
    """Convert a column label to a predictable snake_case string."""
    value = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower())
    return value.strip("_")


def prepare_sales_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Validate and standardise a user-provided retail sales table.

    Required: a date column and either revenue/sales or both units and unit_price.
    Optional dimensions are populated with safe defaults. Missing cost is estimated
    at 65% of revenue and marked in the _cost_estimated column.
    """
    if raw is None or raw.empty:
        raise ValueError("The uploaded file is empty.")

    df = raw.copy()
    df.columns = [_normalise_name(col) for col in df.columns]

    for canonical, alternatives in ALIASES.items():
        if canonical not in df.columns:
            match = next((name for name in alternatives if name in df.columns), None)
            if match:
                df = df.rename(columns={match: canonical})

    if "order_date" not in df.columns:
        raise ValueError("A date column is required (for example: order_date, date or order date).")

    if "revenue" not in df.columns and not {"units", "unit_price"}.issubset(df.columns):
        raise ValueError("Provide a sales/revenue column, or both units/quantity and unit_price/price.")

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.loc[df["order_date"].notna()].copy()
    if df.empty:
        raise ValueError("No valid dates were found. Check the date column format.")

    if "units" in df.columns:
        df["units"] = pd.to_numeric(df["units"], errors="coerce")
    else:
        df["units"] = 1.0
    df["units"] = df["units"].fillna(0.0)

    if "unit_price" in df.columns:
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

    if "revenue" in df.columns:
        df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    else:
        df["revenue"] = df["units"] * df["unit_price"]

    df = df.loc[df["revenue"].notna() & np.isfinite(df["revenue"])].copy()
    if df.empty:
        raise ValueError("No usable sales values were found in the revenue column.")

    if "cost" not in df.columns:
        df["cost"] = np.nan
    df["cost"] = pd.to_numeric(df["cost"], errors="coerce")
    cost_estimated_mask = df["cost"].isna()
    df.loc[cost_estimated_mask, "cost"] = df.loc[cost_estimated_mask, "revenue"] * 0.65

    if "profit" in df.columns:
        df["profit"] = pd.to_numeric(df["profit"], errors="coerce")
        df["profit"] = df["profit"].fillna(df["revenue"] - df["cost"])
    else:
        df["profit"] = df["revenue"] - df["cost"]

    defaults = {"product": "Unknown", "category": "Uncategorised", "region": "Unknown"}
    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default
        df[column] = df[column].fillna(default).astype(str).replace("", default)

    if "order_id" not in df.columns:
        df["order_id"] = [f"ROW-{i + 1}" for i in range(len(df))]
    else:
        df["order_id"] = df["order_id"].fillna("").astype(str)
        blank = df["order_id"].str.strip().eq("")
        df.loc[blank, "order_id"] = [f"ROW-{i + 1}" for i in range(int(blank.sum()))]

    df["units"] = df["units"].astype(float)
    df["revenue"] = df["revenue"].astype(float)
    df["cost"] = df["cost"].astype(float)
    df["profit"] = df["profit"].astype(float)
    df["_cost_estimated"] = cost_estimated_mask.astype(bool)
    return df.sort_values("order_date").reset_index(drop=True)


def monthly_revenue(data: pd.DataFrame) -> pd.Series:
    """Return a month-start indexed revenue series, filling missing months with zero."""
    if data.empty:
        return pd.Series(dtype=float, name="revenue")
    monthly = data.set_index("order_date")["revenue"].resample("MS").sum()
    monthly.name = "revenue"
    return monthly.astype(float)


def sales_summary(data: pd.DataFrame) -> dict[str, float]:
    """Calculate the headline KPIs used by the dashboard."""
    revenue = float(data["revenue"].sum())
    profit = float(data["profit"].sum())
    orders = int(data["order_id"].nunique())
    units = float(data["units"].sum())
    return {
        "revenue": revenue,
        "profit": profit,
        "orders": float(orders),
        "units": units,
        "average_order_value": revenue / orders if orders else 0.0,
        "profit_margin": (profit / revenue * 100.0) if revenue else 0.0,
    }


def revenue_anomalies(data: pd.DataFrame) -> pd.DataFrame:
    """Flag monthly revenue outside the 1.5-IQR range."""
    series = monthly_revenue(data)
    result = series.rename_axis("month").reset_index()
    result.columns = ["month", "revenue"]
    result["is_anomaly"] = False
    result["direction"] = "Normal"
    if len(result) >= 6:
        q1 = float(result["revenue"].quantile(0.25))
        q3 = float(result["revenue"].quantile(0.75))
        spread = q3 - q1
        if spread > 0:
            lower, upper = q1 - 1.5 * spread, q3 + 1.5 * spread
            low = result["revenue"] < lower
            high = result["revenue"] > upper
            result.loc[low | high, "is_anomaly"] = True
            result.loc[low, "direction"] = "Unusually low"
            result.loc[high, "direction"] = "Unusually high"
    return result
