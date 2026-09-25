import frappe


def execute():
	for name in frappe.get_all(
		"Stock Reservation Entry",
		filters={"docstatus": 1, "reservation_based_on": "Serial and Batch"},
		or_filters={"transferred_qty": (">", 0), "consumed_qty": (">", 0)},
		pluck="name",
	):
		frappe.get_doc("Stock Reservation Entry", name).mark_unmatched_rows_as_used()
