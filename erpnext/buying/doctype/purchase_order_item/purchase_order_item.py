# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document

from erpnext.controllers.print_settings import print_settings_for_item_table

class PurchaseOrderItem(Document):
	def __setup__(self):
		print_settings_for_item_table(self)

def on_doctype_update():
	frappe.db.add_index("Purchase Order Item", ["item_code", "warehouse"])

@frappe.whitelist()
def check_item_delete(cdt, cdn):
	dn = frappe.db.sql_list("""select t1.name from `tabPurchase Receipt` t1,`tabPurchase Receipt Item` t2
			where t1.name = t2.parent and t2.purchase_order_item = %s""", cdn)
	if dn:
		return {"code": "no_delete" , "msg": dn}
	else:
		return {"code": "" , "msg": ""}
