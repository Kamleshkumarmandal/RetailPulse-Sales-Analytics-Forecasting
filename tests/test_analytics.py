import pandas as pd
import pytest

from sales_analytics import prepare_sales_data, monthly_revenue, sales_summary, revenue_anomalies
from forecasting import forecast_monthly_revenue


def test_prepare_sales_data_accepts_common_column_names_and_estimates_cost():
    raw = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "Sales": [100.0, 200.0],
        "Quantity": [2, 4],
        "Item": ["A", "B"],
    })
    result = prepare_sales_data(raw)
    assert result["revenue"].sum() == pytest.approx(300.0)
    assert result["profit"].sum() == pytest.approx(105.0)
    assert result["_cost_estimated"].all()
    assert result["category"].eq("Uncategorised").all()


def test_revenue_can_be_derived_from_units_and_unit_price():
    raw = pd.DataFrame({
        "order_date": ["2024-01-01"],
        "units": [3],
        "unit_price": [25],
        "cost": [40],
    })
    result = prepare_sales_data(raw)
    assert result.loc[0, "revenue"] == pytest.approx(75.0)
    assert result.loc[0, "profit"] == pytest.approx(35.0)


def test_missing_dates_are_removed_and_monthly_revenue_is_grouped():
    raw = pd.DataFrame({
        "date": ["2024-01-03", "2024-01-14", "not-a-date"],
        "sales": [10, 20, 500],
    })
    result = prepare_sales_data(raw)
    series = monthly_revenue(result)
    assert len(result) == 2
    assert series.iloc[0] == pytest.approx(30.0)


def test_sales_summary_counts_unique_orders():
    raw = pd.DataFrame({
        "order_date": ["2024-01-01", "2024-01-01"],
        "revenue": [40, 60],
        "order_id": ["same", "same"],
    })
    result = prepare_sales_data(raw)
    summary = sales_summary(result)
    assert summary["orders"] == 1
    assert summary["revenue"] == pytest.approx(100.0)


def test_forecast_returns_requested_future_months():
    dates = pd.date_range("2023-01-01", periods=18, freq="MS")
    raw = pd.DataFrame({
        "order_date": dates,
        "revenue": [1000 + i * 35 + (i % 4) * 70 for i in range(18)],
    })
    result = prepare_sales_data(raw)
    forecast = forecast_monthly_revenue(result, horizon=3)
    assert len(forecast) == 3
    assert forecast["forecast_month"].iloc[0] == pd.Timestamp("2024-07-01")
    assert (forecast["forecast_revenue"] >= 0).all()


def test_forecast_explains_insufficient_history():
    raw = pd.DataFrame({
        "order_date": pd.date_range("2024-01-01", periods=5, freq="MS"),
        "revenue": [10, 12, 11, 14, 15],
    })
    result = prepare_sales_data(raw)
    with pytest.raises(ValueError, match="8 months"):
        forecast_monthly_revenue(result)


def test_missing_cost_values_are_estimated_only_for_missing_rows():
    raw = pd.DataFrame({
        "order_date": ["2024-01-01", "2024-01-02"],
        "revenue": [100.0, 200.0],
        "cost": [30.0, None],
    })
    result = prepare_sales_data(raw)
    assert result["cost"].tolist() == pytest.approx([30.0, 130.0])
    assert result["_cost_estimated"].tolist() == [False, True]
    assert result["profit"].tolist() == pytest.approx([70.0, 70.0])
