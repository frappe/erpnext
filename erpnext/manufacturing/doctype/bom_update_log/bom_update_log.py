# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from erpnext.manufacturing.doctype.bom.bom import get_boms_in_bottom_up_order

from rq.timeouts import JobTimeoutException


class BOMMissingError(frappe.ValidationError): pass

class BOMUpdateLog(Document):
	def validate(self):
		self.validate_boms_are_specified()
		self.validate_same_bom()
		self.validate_bom_items()
		self.status = "Queued"

	def validate_boms_are_specified(self):
		if self.update_type == "Replace BOM" and not (self.current_bom and self.new_bom):
			frappe.throw(
				msg=_("Please mention the Current and New BOM for replacement."),
				title=_("Mandatory"), exc=BOMMissingError
			)

	def validate_same_bom(self):
		if cstr(self.current_bom) == cstr(self.new_bom):
			frappe.throw(_("Current BOM and New BOM can not be same"))

	def validate_bom_items(self):
		current_bom_item = frappe.db.get_value("BOM", self.current_bom, "item")
		new_bom_item = frappe.db.get_value("BOM", self.new_bom, "item")

		if current_bom_item != new_bom_item:
			frappe.throw(_("The selected BOMs are not for the same item"))

	def on_submit(self):
		if frappe.flags.in_test:
			return

		if self.update_type == "Replace BOM":
			boms = {
				"current_bom": self.current_bom,
				"new_bom": self.new_bom
			}
			frappe.enqueue(
				method="erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.replace_bom",
				boms=boms, doc=self, timeout=40000
			)
		else:
			frappe.enqueue(
				method="erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.update_cost_queue",
				doc=self, timeout=40000
			)

def replace_bom(boms, doc):
	try:
		doc.db_set("status", "In Progress")
		if not frappe.flags.in_test:
			frappe.db.commit()

		frappe.db.auto_commit_on_many_writes = 1

		args = frappe._dict(boms)
		doc = frappe.get_doc("BOM Update Tool")
		doc.current_bom = args.current_bom
		doc.new_bom = args.new_bom
		doc.replace_bom()

		doc.db_set("status", "Completed")

	except (Exception, JobTimeoutException):
		frappe.db.rollback()
		frappe.log_error(
			msg=frappe.get_traceback(),
			title=_("BOM Update Tool Error")
		)
		doc.db_set("status", "Failed")

	finally:
		frappe.db.auto_commit_on_many_writes = 0
		frappe.db.commit()

def update_cost_queue(doc):
	try:
		doc.db_set("status", "In Progress")
		if not frappe.flags.in_test:
			frappe.db.commit()

		frappe.db.auto_commit_on_many_writes = 1

		bom_list = get_boms_in_bottom_up_order()
		for bom in bom_list:
			frappe.get_doc("BOM", bom).update_cost(update_parent=False, from_child_bom=True)

		doc.db_set("status", "Completed")

	except (Exception, JobTimeoutException):
		frappe.db.rollback()
		frappe.log_error(
			msg=frappe.get_traceback(),
			title=_("BOM Update Tool Error")
		)
		doc.db_set("status", "Failed")

	finally:
		frappe.db.auto_commit_on_many_writes = 0
		frappe.db.commit()

def update_cost():
	bom_list = get_boms_in_bottom_up_order()
	for bom in bom_list:
		frappe.get_doc("BOM", bom).update_cost(update_parent=False, from_child_bom=True)