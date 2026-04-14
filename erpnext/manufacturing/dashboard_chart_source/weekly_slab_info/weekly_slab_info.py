import frappe


def get_config():
	return {
		"name": "Weekly Slab Info",
		"method": "erpnext.manufacturing.dashboard_chart.weekly_slab_report.weekly_slab_report.get_weekly_slab_report_data",
		"timeseries": 0,
	}
