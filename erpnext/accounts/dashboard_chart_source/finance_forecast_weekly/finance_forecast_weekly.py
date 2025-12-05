import frappe

def get_config():
    return {
        "name": "Finance Forecast Weekly",
        "method": "erpnext.accounts.dashboard_chart.weekly_forecast.weekly_forecast.get_weekly_forecast_finance_chart_data",
        "timeseries": 0
    }
