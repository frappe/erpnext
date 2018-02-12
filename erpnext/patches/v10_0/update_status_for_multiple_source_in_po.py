# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	'''Update the status in material request and sales order'''

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
			po_doc.validate_qty()

		except Exception:
			pass