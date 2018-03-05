# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():


	# update the sales order item in the material request
	frappe.reload_doc('stock', 'doctype', 'material_request_item')
	frappe.db.sql('''update `tabMaterial Request Item` mri set sales_order_item = (select name from
		`tabSales Order Item` soi where soi.parent=mri.sales_order and soi.item_code=mri.item_code) where docstatus = 1 and
		ifnull(mri.sales_order, "")!="" 
	''')

	# update the sales order item in the purchase order
	frappe.db.sql('''update `tabPurchase Order Item` poi set sales_order_item = (select name from
		`tabSales Order Item` soi where soi.parent=poi.sales_order and soi.item_code=poi.item_code) where docstatus = 1 and
		ifnull(poi.sales_order, "")!="" 
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
