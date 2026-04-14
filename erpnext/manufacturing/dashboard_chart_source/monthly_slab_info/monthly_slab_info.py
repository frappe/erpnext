import frappe


def get_config():
	return {
		"name": "Monthly Slab Info",
		"method": "erpnext.manufacturing.dashboard_chart.monthly_slab_report.monthly_slab_report.get_monthly_slab_report_data",
		"timeseries": 0,
	}
