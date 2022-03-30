# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from typing import Dict, List, Literal, Optional

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, flt

from erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool import update_cost


class BOMMissingError(frappe.ValidationError):
	pass


class BOMUpdateLog(Document):
	def validate(self):
		if self.update_type == "Replace BOM":
			self.validate_boms_are_specified()
			self.validate_same_bom()
			self.validate_bom_items()

		self.status = "Queued"

	def validate_boms_are_specified(self):
		if self.update_type == "Replace BOM" and not (self.current_bom and self.new_bom):
			frappe.throw(
				msg=_("Please mention the Current and New BOM for replacement."),
				title=_("Mandatory"),
				exc=BOMMissingError,
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
			boms = {"current_bom": self.current_bom, "new_bom": self.new_bom}
			frappe.enqueue(
				method="erpnext.manufacturing.doctype.bom_update_log.bom_update_log.run_bom_job",
				doc=self,
				boms=boms,
				timeout=40000,
			)
		else:
			frappe.enqueue(
				method="erpnext.manufacturing.doctype.bom_update_log.bom_update_log.run_bom_job",
				doc=self,
				update_type="Update Cost",
				timeout=40000,
			)


def replace_bom(boms: Dict) -> None:
	"""Replace current BOM with new BOM in parent BOMs."""
	current_bom = boms.get("current_bom")
	new_bom = boms.get("new_bom")

	unit_cost = get_new_bom_unit_cost(new_bom)
	update_new_bom_in_bom_items(unit_cost, current_bom, new_bom)

	frappe.cache().delete_key("bom_children")
	parent_boms = get_parent_boms(new_bom)

	for bom in parent_boms:
		bom_obj = frappe.get_doc("BOM", bom)
		# this is only used for versioning and we do not want
		# to make separate db calls by using load_doc_before_save
		# which proves to be expensive while doing bulk replace
		bom_obj._doc_before_save = bom_obj
		bom_obj.update_exploded_items()
		bom_obj.calculate_cost()
		bom_obj.update_parent_cost()
		bom_obj.db_update()
		if bom_obj.meta.get("track_changes") and not bom_obj.flags.ignore_version:
			bom_obj.save_version()


def update_new_bom_in_bom_items(unit_cost: float, current_bom: str, new_bom: str) -> None:
	bom_item = frappe.qb.DocType("BOM Item")
	(
		frappe.qb.update(bom_item)
		.set(bom_item.bom_no, new_bom)
		.set(bom_item.rate, unit_cost)
		.set(bom_item.amount, (bom_item.stock_qty * unit_cost))
		.where(
			(bom_item.bom_no == current_bom) & (bom_item.docstatus < 2) & (bom_item.parenttype == "BOM")
		)
	).run()


def get_parent_boms(new_bom: str, bom_list: Optional[List] = None) -> List:
	bom_list = bom_list or []
	bom_item = frappe.qb.DocType("BOM Item")

	parents = (
		frappe.qb.from_(bom_item)
		.select(bom_item.parent)
		.where((bom_item.bom_no == new_bom) & (bom_item.docstatus < 2) & (bom_item.parenttype == "BOM"))
		.run(as_dict=True)
	)

	for d in parents:
		if new_bom == d.parent:
			frappe.throw(_("BOM recursion: {0} cannot be child of {1}").format(new_bom, d.parent))

		bom_list.append(d.parent)
		get_parent_boms(d.parent, bom_list)

	return list(set(bom_list))


def get_new_bom_unit_cost(new_bom: str) -> float:
	bom = frappe.qb.DocType("BOM")
	new_bom_unitcost = (
		frappe.qb.from_(bom).select(bom.total_cost / bom.quantity).where(bom.name == new_bom).run()
	)

	return flt(new_bom_unitcost[0][0])


def run_bom_job(
	doc: "BOMUpdateLog",
	boms: Optional[Dict[str, str]] = None,
	update_type: Literal["Replace BOM", "Update Cost"] = "Replace BOM",
) -> None:
	try:
		doc.db_set("status", "In Progress")
		if not frappe.flags.in_test:
			frappe.db.commit()

		frappe.db.auto_commit_on_many_writes = 1

		boms = frappe._dict(boms or {})

		if update_type == "Replace BOM":
			replace_bom(boms)
		else:
			update_cost()

		doc.db_set("status", "Completed")

	except Exception:
		frappe.db.rollback()
		error_log = frappe.log_error(message=frappe.get_traceback(), title=_("BOM Update Tool Error"))

		doc.db_set("status", "Failed")
		doc.db_set("error_log", error_log.name)

	finally:
		frappe.db.auto_commit_on_many_writes = 0
		frappe.db.commit()  # nosemgrep
