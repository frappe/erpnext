# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():


	# update the sales order item in the material request
	frappe.reload_doc('stock', 'doctype', 'material_request_item')
	frappe.db.sql('''update `tabMaterial Request Item` mri, `tabSales Order Item` soi
		set mri.sales_order_item = soi.name
		where ifnull(mri.sales_order, "")!="" and soi.parent=mri.sales_order
		and soi.item_code=mri.item_code and mri.docstatus=1
	''')

	# update the sales order item in the purchase order
	frappe.db.sql('''update `tabPurchase Order Item` poi, `tabSales Order Item` soi
		set poi.sales_order_item = soi.name
		where ifnull(poi.sales_order, "")!="" and soi.parent=poi.sales_order
		and soi.item_code=poi.item_code and poi.docstatus = 1
	''')

	# Update the status in material request and sales order
	po_list = frappe.db.sql('''
			select parent from `tabPurchase Order Item` where ifnull(material_request, "")!="" and
			ifnull(sales_order, "")!="" and docstatus=1
		''',as_dict=1)

	for po in list(set([d.get("parent") for d in po_list if d.get("parent")])):
		try:
			po_doc = frappe.get_doc("Purchase Order", po)

			# update the so in the status updater
			po_doc.update_status_updater()
			po_doc.update_qty(update_modified=False)

		except Exception:
			pass
