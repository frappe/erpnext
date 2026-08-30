import frappe


def execute():
	supplier_quotations = frappe.get_all(
		"Purchase Order Item",
		filters={
			"docstatus": 1,
			"supplier_quotation": ["is", "set"],
			"supplier_quotation_item": ["is", "set"],
		},
		pluck="supplier_quotation",
		distinct=True,
	)

	for supplier_quotation in supplier_quotations:
		doc = frappe.get_doc("Supplier Quotation", supplier_quotation)
		if doc.docstatus == 1:
			doc.set_status(update=True, update_modified=False)
