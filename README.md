# RetailPulse — Sales Analytics & Forecasting

[![Open Live Demo](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://retailpulse-sales-analytics-forecasting-nsmurdecucfes7vhyswcbi.streamlit.app/)

**Live Demo:** [RetailPulse – Sales Analytics & Forecasting](https://retailpulse-sales-analytics-forecasting-nsmurdecucfes7vhyswcbi.streamlit.app/)


RetailPulse is a Streamlit dashboard for exploring retail sales, tracking business KPIs, spotting unusual monthly sales changes, and forecasting revenue from uploaded CSV or Excel data.

## Features

- Upload CSV or Excel sales files, or explore the included sample dataset.
- Track revenue, profit, orders, units sold, average order value and profit margin.
- Filter results by date, product category, product and region.
- Explore monthly sales trends and product/category/region performance.
- Forecast monthly revenue with a scikit-learn regression model.
- Flag unusually high or low monthly revenue using an IQR-based rule.
- Download filtered data and forecast results as CSV.

## Run locally

Python 3.10 or newer is recommended.

```bash
# Windows PowerShell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

On macOS/Linux, activate the environment with `source .venv/bin/activate`.

## Input data

Upload a CSV or Excel file. The app recognizes common alternatives such as `date`, `order date`, `sales`, `quantity`, and `item`. At minimum, provide a date column and either a revenue/sales column or both units and unit price. Product, category, region and cost are optional; missing descriptive fields are filled with "Unknown" / "Uncategorised", and missing cost is estimated at 65% of revenue so the displayed profit estimate is clearly marked.

Expected canonical columns:

| Column | Required | Meaning |
|---|---|---|
| `order_date` | Yes | Transaction date |
| `revenue` | Yes, or units + unit_price | Sales amount |
| `units` | Optional | Quantity sold |
| `unit_price` | Optional | Price per unit |
| `cost` | Optional | Total cost |
| `profit` | Optional | Profit; otherwise revenue minus cost |
| `order_id` | Optional | Order identifier |
| `product`, `category`, `region` | Optional | Product and market dimensions |

## Forecasting notes

The forecast is an analytical estimate trained on the selected data, not a guarantee. It uses a Random Forest regression model with calendar and recent-sales features. It requires enough monthly history to fit a useful model; otherwise the dashboard explains why it cannot produce a forecast. No external service receives uploaded data.

## Tests

```bash
pytest -q
```

## Deploy

Create a new app in [Streamlit Community Cloud](https://share.streamlit.io), select this repository, choose `app.py` as the main file, and deploy. The repository includes `requirements.txt`.

## Data

`sample_data.csv` is synthetic demonstration data created for this project. It does not represent a real retailer or actual customer transactions.

## License

MIT — see [LICENSE](LICENSE).
