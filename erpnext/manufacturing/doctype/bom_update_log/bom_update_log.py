# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import json
from typing import Any, Dict, List, Optional, Tuple, Union

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr

from erpnext.manufacturing.doctype.bom_update_log.bom_updation_utils import (
	get_leaf_boms,
	get_next_higher_level_boms,
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
		else:
			self.validate_bom_cost_update_in_progress()

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

	def validate_bom_cost_update_in_progress(self):
		"If another Cost Updation Log is still in progress, dont make new ones."

		wip_log = frappe.get_all(
			"BOM Update Log",
			{"update_type": "Update Cost", "status": ["in", ["Queued", "In Progress"]]},
			limit_page_length=1,
		)
		if wip_log:
			log_link = frappe.utils.get_link_to_form("BOM Update Log", wip_log[0].name)
			frappe.throw(
				_("BOM Updation already in progress. Please wait until {0} is complete.").format(log_link),
				title=_("Note"),
			)

	def on_submit(self):
		if self.update_type == "Replace BOM":
			boms = {"current_bom": self.current_bom, "new_bom": self.new_bom}
			frappe.enqueue(
				method="erpnext.manufacturing.doctype.bom_update_log.bom_update_log.run_replace_bom_job",
				doc=self,
				boms=boms,
				timeout=40000,
				now=frappe.flags.in_test,
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
		replace_bom(boms, doc.name)

		doc.db_set("status", "Completed")
	except Exception:
		handle_exception(doc)
	finally:
		frappe.db.auto_commit_on_many_writes = 0

		if not frappe.flags.in_test:
			frappe.db.commit()  # nosemgrep


def process_boms_cost_level_wise(
	update_doc: "BOMUpdateLog", parent_boms: List[str] = None
) -> Union[None, Tuple]:
	"Queue jobs at the start of new BOM Level in 'Update Cost' Jobs."

	current_boms = {}
	values = {}

	if update_doc.status == "Queued":
		# First level yet to process. On Submit.
		current_level = 0
		current_boms = get_leaf_boms()
		values = {
			"processed_boms": json.dumps({}),
			"status": "In Progress",
			"current_level": current_level,
		}
	else:
		# Resume next level. via Cron Job.
		if not parent_boms:
			return

		current_level = cint(update_doc.current_level) + 1

		# Process the next level BOMs. Stage parents as current BOMs.
		current_boms = parent_boms.copy()
		values = {"current_level": current_level}

	set_values_in_log(update_doc.name, values, commit=True)
	queue_bom_cost_jobs(current_boms, update_doc, current_level)


def queue_bom_cost_jobs(
	current_boms_list: List[str], update_doc: "BOMUpdateLog", current_level: int
) -> None:
	"Queue batches of 20k BOMs of the same level to process parallelly"
	batch_no = 0

	while current_boms_list:
		batch_no += 1
		batch_size = 20_000
		boms_to_process = current_boms_list[:batch_size]  # slice out batch of 20k BOMs

		# update list to exclude 20K (queued) BOMs
		current_boms_list = current_boms_list[batch_size:] if len(current_boms_list) > batch_size else []

		batch_row = update_doc.append(
			"bom_batches", {"level": current_level, "batch_no": batch_no, "status": "Pending"}
		)
		batch_row.db_insert()

		frappe.enqueue(
			method="erpnext.manufacturing.doctype.bom_update_log.bom_updation_utils.update_cost_in_level",
			doc=update_doc,
			bom_list=boms_to_process,
			batch_name=batch_row.name,
			queue="long",
			now=frappe.flags.in_test,
		)


def resume_bom_cost_update_jobs():
	"""
	1. Checks for In Progress BOM Update Log.
	2. Checks if this job has completed the _current level_.
	3. If current level is complete, get parent BOMs and start next level.
	4. If no parents, mark as Complete.
	5. If current level is WIP, skip the Log.

	Called every 5 minutes via Cron job.
	"""

	in_progress_logs = frappe.db.get_all(
		"BOM Update Log",
		{"update_type": "Update Cost", "status": "In Progress"},
		["name", "processed_boms", "current_level"],
	)
	if not in_progress_logs:
		return

	for log in in_progress_logs:
		# check if all log batches of current level are processed
		bom_batches = frappe.db.get_all(
			"BOM Update Batch",
			{"parent": log.name, "level": log.current_level},
			["name", "boms_updated", "status"],
		)
		incomplete_level = any(row.get("status") == "Pending" for row in bom_batches)
		if not bom_batches or incomplete_level:
			continue

		# Prep parent BOMs & updated processed BOMs for next level
		current_boms, processed_boms = get_processed_current_boms(log, bom_batches)
		parent_boms = get_next_higher_level_boms(child_boms=current_boms, processed_boms=processed_boms)

		# Unset processed BOMs if log is complete, it is used for next level BOMs
		set_values_in_log(
			log.name,
			values={
				"processed_boms": json.dumps([] if not parent_boms else processed_boms),
				"status": "Completed" if not parent_boms else "In Progress",
			},
			commit=True,
		)

		if parent_boms:  # there is a next level to process
			process_boms_cost_level_wise(
				update_doc=frappe.get_doc("BOM Update Log", log.name), parent_boms=parent_boms
			)


def get_processed_current_boms(
	log: Dict[str, Any], bom_batches: Dict[str, Any]
) -> Tuple[List[str], Dict[str, Any]]:
	"""
	Aggregate all BOMs from BOM Update Batch rows into 'processed_boms' field
	and into current boms list.
	"""
	processed_boms = json.loads(log.processed_boms) if log.processed_boms else {}
	current_boms = []

	for row in bom_batches:
		boms_updated = json.loads(row.boms_updated)
		current_boms.extend(boms_updated)
		boms_updated_dict = {bom: True for bom in boms_updated}
		processed_boms.update(boms_updated_dict)

	return current_boms, processed_boms
