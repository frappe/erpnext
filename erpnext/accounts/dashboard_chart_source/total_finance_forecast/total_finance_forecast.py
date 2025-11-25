import frappe

def get_config():
    return {
        "name": "Total Finance Forecast",
        "method": "erpnext.accounts.dashboard_chart.total_forecast.total_forecast.get_overall_forecast_finance_chart_data",
        "timeseries": 0
    }
