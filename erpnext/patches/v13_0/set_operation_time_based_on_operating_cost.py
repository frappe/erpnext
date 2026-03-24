import frappe


def execute():
	frappe.reload_doc("manufacturing", "doctype", "bom")
	frappe.reload_doc("manufacturing", "doctype", "bom_operation")

	for row in frappe.get_all(
		"BOM Operation",
		filters={
			"time_in_mins": 0,
			"operating_cost": [">", 0],
			"hour_rate": [">", 0],
			"docstatus": 1,
			"parenttype": "BOM",
		},
		fields=["name", "operating_cost", "hour_rate"],
	):
		frappe.db.set_value(
			"BOM Operation",
			row.name,
			"time_in_mins",
			(row.operating_cost * 60) / row.hour_rate,
			update_modified=False,
		)
