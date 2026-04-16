import frappe
from frappe import _
from frappe import utils as frappe_utils


@frappe.whitelist()
def get_daily_slab_report_data():
	daily_slab_count = frappe.db.sql(
		"""
        SELECT COUNT(*)
        FROM `tabStock Ledger Entry`
        WHERE DATE(creation) = %s AND
        warehouse LIKE '%%finished goods Warehouse%%'
		AND actual_qty > 0
    """,
		(frappe_utils.today(),),
	)

	daily_slab_cost = frappe.db.sql(
		"""
        SELECT SUM(valuation_rate)
        FROM `tabStock Ledger Entry`
        WHERE DATE(creation) = %s AND
        warehouse LIKE '%%finished goods Warehouse%%'
		AND actual_qty > 0
    """,
		(frappe_utils.today(),),
	)
	return {
		"labels": ["Today"],  # only one label
		"datasets": [
			{"name": "Slab Count", "values": [daily_slab_count[0][0]], "color": "#3DB341"},
			{"name": "Slab Cost", "values": [daily_slab_cost[0][0]], "color": "#DA5248"},
		],
		"type": "bar",
	}
