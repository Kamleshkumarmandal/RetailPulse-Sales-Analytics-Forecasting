"""Small, local monthly revenue forecasting model."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from sales_analytics import monthly_revenue


FEATURE_NAMES = ["trend", "month", "month_sin", "month_cos", "lag_1", "lag_2", "lag_3", "rolling_3"]


def _feature_row(trend: int, month: int, history: list[float]) -> list[float]:
    recent = history[-3:]
    return [
        float(trend),
        float(month),
        float(np.sin(2 * np.pi * month / 12.0)),
        float(np.cos(2 * np.pi * month / 12.0)),
        float(history[-1]),
        float(history[-2]),
        float(history[-3]),
        float(np.mean(recent)),
    ]


def forecast_monthly_revenue(data: pd.DataFrame, horizon: int = 6) -> pd.DataFrame:
    """Fit a Random Forest to monthly history and recursively forecast future months.

    At least eight monthly observations are required. Returned values are point
    estimates; this function does not claim calibrated confidence intervals.
    """
    if not 1 <= int(horizon) <= 12:
        raise ValueError("Forecast horizon must be between 1 and 12 months.")

    series = monthly_revenue(data).asfreq("MS", fill_value=0.0)
    if len(series) < 8:
        raise ValueError("At least 8 months of sales history are required for forecasting.")

    values = [float(value) for value in series.to_numpy()]
    dates = list(series.index)
    features, targets = [], []
    for index in range(3, len(values)):
        features.append(_feature_row(index, dates[index].month, values[:index]))
        targets.append(values[index])

    model = RandomForestRegressor(
        n_estimators=250,
        max_depth=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=1,
    )
    model.fit(np.asarray(features), np.asarray(targets))

    history = values.copy()
    last_month = dates[-1]
    predictions = []
    for step in range(1, int(horizon) + 1):
        next_month = last_month + pd.offsets.MonthBegin(step)
        row = _feature_row(len(history), next_month.month, history)
        predicted = max(0.0, float(model.predict(np.asarray([row]))[0]))
        predictions.append({"forecast_month": next_month, "forecast_revenue": predicted})
        history.append(predicted)

    return pd.DataFrame(predictions)
