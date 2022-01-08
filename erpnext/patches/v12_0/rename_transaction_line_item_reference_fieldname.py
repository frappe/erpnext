import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	dts = [
		'Quotation Item', 'Sales Order Item', 'Delivery Note Item', 'Sales Invoice Item',
		'Supplier Quotation Item', 'Purchase Order Item', 'Purchase Receipt Item', 'Purchase Invoice Item'
	]

	rename_map = {
		'so_detail': 'sales_order_item',
		'dn_detail': 'delivery_note_item',
		'si_detail': 'sales_invoice_item',
		'po_detail': 'purchase_order_item',
		'pr_detail': 'purchase_receipt_item',
		'pi_detail': 'purchase_invoice_item',
		'against_sales_order': 'sales_order',
		'against_sales_invoice': 'sales_invoice',
	}

	for dt in dts:
		frappe.reload_doctype(dt)

		if dt == "Sales Order":
			if frappe.db.has_column(dt, 'prevdoc_docname'):
				rename_field(dt, 'prevdoc_docname', 'quotation')

		for old_fieldname, new_fieldname in rename_map.items():
			if frappe.db.has_column(dt, old_fieldname):
				rename_field(dt, old_fieldname, new_fieldname)
