import frappe


def get_config():
	return {
		"name": "Daily Slab Info",
		"method": "erpnext.manufacturing.dashboard_chart.daily_slab_report.daily_slab_report.get_daily_slab_report_data",
		"timeseries": 0,
	}
