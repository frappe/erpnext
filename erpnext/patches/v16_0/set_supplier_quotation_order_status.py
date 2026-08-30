import frappe

from erpnext.buying.doctype.purchase_order.services.status import update_supplier_quotation_status


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

	update_supplier_quotation_status(supplier_quotations, update_modified=False)
