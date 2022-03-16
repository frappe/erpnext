# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import click
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, flt

from erpnext.manufacturing.doctype.bom_update_log.bom_update_log import update_cost


class BOMUpdateTool(Document):
	def replace_bom(self):
		unit_cost = get_new_bom_unit_cost(self.new_bom)
		self.update_new_bom(unit_cost)

		frappe.cache().delete_key('bom_children')
		bom_list = self.get_parent_boms(self.new_bom)

		with click.progressbar(bom_list) as bom_list:
			pass
		for bom in bom_list:
			try:
				bom_obj = frappe.get_cached_doc('BOM', bom)
				# this is only used for versioning and we do not want
				# to make separate db calls by using load_doc_before_save
				# which proves to be expensive while doing bulk replace
				bom_obj._doc_before_save = bom_obj
				bom_obj.update_new_bom(self.current_bom, self.new_bom, unit_cost)
				bom_obj.update_exploded_items()
				bom_obj.calculate_cost()
				bom_obj.update_parent_cost()
				bom_obj.db_update()
				if bom_obj.meta.get('track_changes') and not bom_obj.flags.ignore_version:
					bom_obj.save_version()
			except Exception:
				frappe.log_error(frappe.get_traceback())

	def update_new_bom(self, unit_cost):
		frappe.db.sql("""update `tabBOM Item` set bom_no=%s,
			rate=%s, amount=stock_qty*%s where bom_no = %s and docstatus < 2 and parenttype='BOM'""",
			(self.new_bom, unit_cost, unit_cost, self.current_bom))

	def get_parent_boms(self, bom, bom_list=None):
		if bom_list is None:
			bom_list = []
		data = frappe.db.sql("""SELECT DISTINCT parent FROM `tabBOM Item`
			WHERE bom_no = %s AND docstatus < 2 AND parenttype='BOM'""", bom)

		for d in data:
			if self.new_bom == d[0]:
				frappe.throw(_("BOM recursion: {0} cannot be child of {1}").format(bom, self.new_bom))

			bom_list.append(d[0])
			self.get_parent_boms(d[0], bom_list)

		return list(set(bom_list))

def get_new_bom_unit_cost(bom):
	new_bom_unitcost = frappe.db.sql("""SELECT `total_cost`/`quantity`
		FROM `tabBOM` WHERE name = %s""", bom)

	return flt(new_bom_unitcost[0][0]) if new_bom_unitcost else 0

@frappe.whitelist()
def enqueue_replace_bom(args):
	if isinstance(args, str):
		args = json.loads(args)

	create_bom_update_log(boms=args)
	frappe.msgprint(_("Queued for replacing the BOM. It may take a few minutes."))


@frappe.whitelist()
def enqueue_update_cost():
	create_bom_update_log(update_type="Update Cost")
	frappe.msgprint(_("Queued for updating latest price in all Bill of Materials. It may take a few minutes."))


def auto_update_latest_price_in_all_boms():
	"Called via hooks.py."
	if frappe.db.get_single_value("Manufacturing Settings", "update_bom_costs_automatically"):
		update_cost()

def create_bom_update_log(boms=None, update_type="Replace BOM"):
	"Creates a BOM Update Log that handles the background job."
	current_bom = boms.get("current_bom") if boms else None
	new_bom = boms.get("new_bom") if boms else None
	log_doc = frappe.get_doc({
		"doctype": "BOM Update Log",
		"current_bom": current_bom,
		"new_bom": new_bom,
		"update_type": update_type
	})
	log_doc.submit()