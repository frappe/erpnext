import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "Landed Cost Item")

	rows = frappe.get_all("Landed Cost Item", fields=['name', 'purchase_receipt_item', 'purchase_invoice_item'])
	for d in rows:
		uom = None
		if d.purchase_receipt_item:
			uom = frappe.db.get_value("Purchase Receipt Item", d.purchase_receipt_item, 'uom')
		elif d.purchase_invoice_item:
			uom = frappe.db.get_value("Purchase Invoice Item", d.purchase_invoice_item, 'uom')

		if uom:
			frappe.db.set_value("Landed Cost Item", d.name, 'uom', uom, update_modified=False)
