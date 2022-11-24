# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AssetTransfer(Document):
	def validate(self):
		if self.from_warehouse and self.to_warehouse and self.from_warehouse == self.to_warehouse:
			frappe.throw("From and To Warehouse cannot be the same.")
	def check_qty(self):
		if not self.purchase_receipt:
			frappe.throw("Please select Purchase Receipt.")
		if not self.item_code:
			frappe.throw("Please select Material Code.")
		if not self.from_warehouse:
			frappe.throw("Please select From Warehouse.")
		total_qty = frappe.db.sql("""select sum(ifnull(qty,0)) total_qty 
								  from `tabAsset Received Entries`
								  where item_code="{}"
								  and ref_doc = "{}"
								  and docstatus = 1""".format(self.item_code, self.purchase_receipt))[0][0]
		issued_qty = frappe.db.sql("""select sum(ifnull(qty,0)) issued_qty
								   from `tabAsset Issue Details` 
								   where item_code ="{}"
								   and warehouse = "{}"
								   and purchase_receipt = "{}"
								   and docstatus = 1""".format(self.item_code, self.from_warehouse, self.purchase_receipt))[0][0]
		
		transferred_to_qty = frappe.db.sql("""select sum(ifnull(transfer_qty,0)) issued_qty
								   from `tabAsset Transfer` 
								   where item_code ="{}"
								   and purchase_receipt = "{}"
								   and to_warehouse = "{}"
								   and docstatus = 1 
								   and name != "{}" """.format(self.item_code, self.purchase_receipt, self.from_warehouse, self.name))[0][0]
		transferred_from_qty = frappe.db.sql("""select sum(ifnull(transfer_qty,0)) issued_qty
								   from `tabAsset Transfer` 
								   where item_code ="{}"
								   and purchase_receipt = "{}"
								   and from_warehouse = "{}"
								   and docstatus = 1 
								   and name != "{}" """.format(self.item_code, self.purchase_receipt, self.from_warehouse, self.name))[0][0]
		balance_qty = flt(total_qty) - flt(issued_qty) - flt(transferred_from_qty) + flt(transferred_to_qty)
		if flt(self.transfer_qty) > flt(balance_qty):
			frappe.throw(_("Transfer Quantity cannot be greater than Balance Quantity i.e., {}").format(flt(balance_qty)), title="Insufficient Balance")