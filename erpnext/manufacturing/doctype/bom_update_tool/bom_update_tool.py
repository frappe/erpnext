# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.utils import cstr, flt
from frappe import _
from six import string_types
from erpnext.manufacturing.doctype.bom.bom import get_boms_in_bottom_up_order
from frappe.model.document import Document

class BOMUpdateTool(Document):
	def replace_bom(self):
		self.validate_bom()
		self.update_new_bom()
		bom_list = self.get_parent_boms(self.new_bom)
		updated_bom = []

		for bom in bom_list:
			try:
				bom_obj = frappe.get_doc("BOM", bom)
				bom_obj.get_doc_before_save()
				updated_bom = bom_obj.update_cost_and_exploded_items(updated_bom)
				bom_obj.calculate_cost()
				bom_obj.update_parent_cost()
				bom_obj.db_update()
				if (getattr(bom_obj.meta, 'track_changes', False)
					and bom_obj._doc_before_save and not bom_obj.flags.ignore_version):
					bom_obj.save_version()

				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
				frappe.log_error(frappe.get_traceback())

	def validate_bom(self):
		if cstr(self.current_bom) == cstr(self.new_bom):
			frappe.throw(_("Current BOM and New BOM can not be same"))
			
		if frappe.db.get_value("BOM", self.current_bom, "item") \
			!= frappe.db.get_value("BOM", self.new_bom, "item"):
				frappe.throw(_("The selected BOMs are not for the same item"))

	def update_new_bom(self):
		new_bom_unitcost = frappe.db.sql("""select total_cost/quantity
			from `tabBOM` where name = %s""", self.new_bom)
		new_bom_unitcost = flt(new_bom_unitcost[0][0]) if new_bom_unitcost else 0

		frappe.db.sql("""update `tabBOM Item` set bom_no=%s,
			rate=%s, amount=stock_qty*%s where bom_no = %s and docstatus < 2 and parenttype='BOM'""",
			(self.new_bom, new_bom_unitcost, new_bom_unitcost, self.current_bom))

	def get_parent_boms(self, bom, bom_list=None):
		if not bom_list:
			bom_list = []

		data = frappe.db.sql(""" select distinct parent from `tabBOM Item`
			where ifnull(bom_no, '') = %s and docstatus < 2 and parenttype='BOM'""", bom)

		for d in data:
			bom_list.append(d[0])
			self.get_parent_boms(d[0], bom_list)

		return list(set(bom_list))

@frappe.whitelist()
def enqueue_replace_bom(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	frappe.enqueue("erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.replace_bom", args=args, timeout=4000)
	frappe.msgprint(_("Queued for replacing the BOM. It may take a few minutes."))

@frappe.whitelist()
def enqueue_update_cost():
	frappe.enqueue("erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.update_cost")
	frappe.msgprint(_("Queued for updating latest price in all Bill of Materials. It may take a few minutes."))

def update_latest_price_in_all_boms():
	if frappe.db.get_single_value("Manufacturing Settings", "update_bom_costs_automatically"):
		update_cost()

def replace_bom(args):
	args = frappe._dict(args)

	doc = frappe.get_doc("BOM Update Tool")
	doc.current_bom = args.current_bom
	doc.new_bom = args.new_bom
	doc.replace_bom()

def update_cost():
	bom_list = get_boms_in_bottom_up_order()
	for bom in bom_list:
		frappe.get_doc("BOM", bom).update_cost(update_parent=False, from_child_bom=True)