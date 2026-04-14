import frappe
from frappe import _
from frappe import utils as frappe_utils


@frappe.whitelist()
def get_weekly_slab_report_data():
	start_date = frappe_utils.get_first_day_of_week(frappe_utils.today())
	end_date = frappe_utils.get_last_day_of_week(frappe_utils.today())
	weekly_slab_count = frappe.db.sql(
		"""
		SELECT COUNT(*)
		FROM `tabStock Ledger Entry`
		WHERE DATE(creation) BETWEEN %s AND %s AND
		warehouse LIKE '%%finished goods Warehouse%%'
		AND actual_qty > 0
	""",
		(start_date, end_date),
	)

	weekly_slab_cost = frappe.db.sql(
		"""
		SELECT SUM(valuation_rate)
		FROM `tabStock Ledger Entry`
		WHERE DATE(creation) BETWEEN %s AND %s
		AND warehouse LIKE '%%finished goods Warehouse%%'
		AND actual_qty > 0
	""",
		(start_date, end_date),
	)

	return {
		"labels": ["This Week"],
		"datasets": [
			{"name": "Slab Count", "values": [weekly_slab_count[0][0]], "color": "#3DB341"},
			{"name": "Slab Cost", "values": [weekly_slab_cost[0][0]], "color": "#DA5248"},
		],
		"type": "bar",
	}
