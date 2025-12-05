import frappe

@frappe.whitelist()
def get_forecast_finance_chart_data():
    # Todo : Replace with actual data later
    return {
        "labels": ["Income", "Expenses", "Total Surplus/Deficit"],
        "datasets": [
            {"name": "This Week", "values": [5000, 2000, 3000]},
            {"name": "Total", "values": [20000, 12000, 8000]}
        ],
        "type": "bar"
    }
