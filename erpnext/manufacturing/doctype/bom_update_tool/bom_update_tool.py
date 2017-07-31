# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, flt
from frappe import _
from erpnext.manufacturing.doctype.bom.bom import get_boms_in_bottom_up_order
from frappe.model.document import Document

class BOMUpdateTool(Document):
	def replace_bom(self):
		self.validate_bom()
		self.update_new_bom()
		bom_list = self.get_parent_boms()
		updated_bom = []
		for bom in bom_list:
			bom_obj = frappe.get_doc("BOM", bom)
			updated_bom = bom_obj.update_cost_and_exploded_items(updated_bom)

		frappe.msgprint(_("BOM replaced"))

	def validate_bom(self):
		if cstr(self.current_bom) == cstr(self.new_bom):
			frappe.throw(_("Current BOM and New BOM can not be same"))
			
		if frappe.db.get_value("BOM", self.current_bom, "item") \
			!= frappe.db.get_value("BOM", self.new_bom, "item"):
				frappe.throw(_("The selected BOMs are not for the same item"))

	def update_new_bom(self):
		current_bom_unitcost = frappe.db.sql("""select total_cost/quantity
			from `tabBOM` where name = %s""", self.current_bom)
		current_bom_unitcost = current_bom_unitcost and flt(current_bom_unitcost[0][0]) or 0
		frappe.db.sql("""update `tabBOM Item` set bom_no=%s,
			rate=%s, amount=stock_qty*%s where bom_no = %s and docstatus < 2""",
			(self.new_bom, current_bom_unitcost, current_bom_unitcost, self.current_bom))

	def get_parent_boms(self):
		return [d[0] for d in frappe.db.sql("""select distinct parent
			from `tabBOM Item` where ifnull(bom_no, '') = %s and docstatus < 2""",
			self.new_bom)]

@frappe.whitelist()
def enqueue_update_cost():
	frappe.enqueue("erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.update_cost")
	frappe.msgprint(_("Queued for updating latest price in all Bill of Materials. It may take a few minutes."))

def update_latest_price_in_all_boms():
	if frappe.db.get_single_value("Manufacturing Settings", "update_bom_costs_automatically"):
		update_cost()

def update_cost():
	bom_list = get_boms_in_bottom_up_order()
	for bom in bom_list:
		frappe.get_doc("BOM", bom).update_cost(update_parent=False, from_child_bom=True)