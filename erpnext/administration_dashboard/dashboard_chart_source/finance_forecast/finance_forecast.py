import frappe

def get_config():
    return {
        "name": "Finance Forecast",
        "method": "erpnext.administration_dashboard.dashboard_chart.forecast.forecast.get_forecast_finance_chart_data",
        "timeseries": 0
    }
