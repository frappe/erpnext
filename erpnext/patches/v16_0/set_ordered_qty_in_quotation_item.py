import frappe


def execute():
	data = frappe.get_all(
		"Sales Order Item",
		filters={"quotation_item": ["is", "set"], "docstatus": 1},
		fields=["quotation_item", {"SUM": "stock_qty", "as": "ordered_qty"}],
		group_by="quotation_item",
	)
	if data:
		frappe.db.auto_commit_on_many_writes = 1
		try:
			frappe.db.bulk_update(
				"Quotation Item", {d.quotation_item: {"ordered_qty": d.ordered_qty} for d in data}
			)
			quotations = frappe.get_all(
				"Quotation Item",
				filters={"name": ["in", [d.quotation_item for d in data]]},
				pluck="parent",
				distinct=True,
			)
			for quotation in quotations:
				doc = frappe.get_doc("Quotation", quotation)
				doc.set_status(update=True, update_modified=False)
		finally:
			frappe.db.auto_commit_on_many_writes = 0
