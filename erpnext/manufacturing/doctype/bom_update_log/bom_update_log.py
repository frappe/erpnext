# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import json
from typing import Dict, Optional

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from erpnext.manufacturing.doctype.bom_update_log.bom_updation_utils import (
	get_leaf_boms,
	handle_exception,
	replace_bom,
	set_values_in_log,
)


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
				method="erpnext.manufacturing.doctype.bom_update_log.bom_update_log.run_replace_bom_job",
				doc=self,
				boms=boms,
				timeout=40000,
			)
		else:
			process_boms_cost_level_wise(self)


def run_replace_bom_job(
	doc: "BOMUpdateLog",
	boms: Optional[Dict[str, str]] = None,
) -> None:
	try:
		doc.db_set("status", "In Progress")

		if not frappe.flags.in_test:
			frappe.db.commit()

		frappe.db.auto_commit_on_many_writes = 1
		boms = frappe._dict(boms or {})
		replace_bom(boms)

		doc.db_set("status", "Completed")
	except Exception:
		handle_exception(doc)
	finally:
		frappe.db.auto_commit_on_many_writes = 0
		frappe.db.commit()  # nosemgrep


def process_boms_cost_level_wise(update_doc: "BOMUpdateLog") -> None:
	"Queue jobs at the start of new BOM Level in 'Update Cost' Jobs."

	current_boms, parent_boms = {}, []
	values = {}

	if update_doc.status == "Queued":
		# First level yet to process. On Submit.
		current_boms = {bom: False for bom in get_leaf_boms()}
		values = {
			"current_boms": json.dumps(current_boms),
			"parent_boms": "[]",
			"processed_boms": json.dumps({}),
			"status": "In Progress",
		}
	else:
		# status is Paused, resume. via Cron Job.
		current_boms, parent_boms = json.loads(update_doc.current_boms), json.loads(
			update_doc.parent_boms
		)
		if not current_boms:
			# Process the next level BOMs. Stage parents as current BOMs.
			current_boms = {bom: False for bom in parent_boms}
			values = {
				"current_boms": json.dumps(current_boms),
				"parent_boms": "[]",
				"status": "In Progress",
			}

	set_values_in_log(update_doc.name, values, commit=True)
	queue_bom_cost_jobs(current_boms, update_doc)


def queue_bom_cost_jobs(current_boms: Dict, update_doc: "BOMUpdateLog") -> None:
	"Queue batches of 20k BOMs of the same level to process parallelly"
	current_boms_list = [bom for bom in current_boms]

	while current_boms_list:
		boms_to_process = current_boms_list[:20000]  # slice out batch of 20k BOMs

		# update list to exclude 20K (queued) BOMs
		current_boms_list = current_boms_list[20000:] if len(current_boms_list) > 20000 else []
		frappe.enqueue(
			method="erpnext.manufacturing.doctype.bom_update_log.bom_updation_utils.update_cost_in_level",
			doc=update_doc,
			bom_list=boms_to_process,
			timeout=40000,
		)


def resume_bom_cost_update_jobs():
	"Called every 10 minutes via Cron job."
	paused_jobs = frappe.db.get_all("BOM Update Log", {"status": "Paused"})
	if not paused_jobs:
		return

	for job in paused_jobs:
		# resume from next level
		process_boms_cost_level_wise(update_doc=frappe.get_doc("BOM Update Log", job.name))
