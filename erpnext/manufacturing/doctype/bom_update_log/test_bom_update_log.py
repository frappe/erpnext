# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.bom_update_log.bom_update_log import (
	BOMMissingError,
	get_processed_current_boms,
	process_boms_cost_level_wise,
	queue_bom_cost_jobs,
	run_replace_bom_job,
)
from erpnext.manufacturing.doctype.bom_update_log.bom_updation_utils import (
	get_next_higher_level_boms,
	set_values_in_log,
	update_cost_in_level,
)
from erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool import (
	enqueue_replace_bom,
	enqueue_update_cost,
)

test_records = frappe.get_test_records("BOM")


class TestBOMUpdateLog(FrappeTestCase):
	"Test BOM Update Tool Operations via BOM Update Log."

	def setUp(self):
		bom_doc = frappe.copy_doc(test_records[0])
		bom_doc.items[1].item_code = "_Test Item"
		bom_doc.insert()

		self.boms = frappe._dict(
			current_bom="BOM-_Test Item Home Desktop Manufactured-001",
			new_bom=bom_doc.name,
		)

		self.new_bom_doc = bom_doc

	def tearDown(self):
		frappe.db.rollback()

	def test_bom_update_log_validate(self):
		"""
		1) Test if BOM presence is validated.
		2) Test if same BOMs are validated.
		3) Test of non-existent BOM is validated.
		"""

		with self.assertRaises(BOMMissingError):
			enqueue_replace_bom(boms={})

		with self.assertRaises(frappe.ValidationError):
			enqueue_replace_bom(boms=frappe._dict(current_bom=self.boms.new_bom, new_bom=self.boms.new_bom))

		with self.assertRaises(frappe.ValidationError):
			enqueue_replace_bom(boms=frappe._dict(current_bom=self.boms.new_bom, new_bom="Dummy BOM"))

	def test_bom_update_log_queueing(self):
		"Test if BOM Update Log is created and queued."

		log = enqueue_replace_bom(boms=self.boms)

		self.assertEqual(log.docstatus, 1)
		self.assertEqual(log.status, "Queued")

	def test_bom_update_log_completion(self):
		"Test if BOM Update Log handles job completion correctly."

		log = enqueue_replace_bom(boms=self.boms)

		# Is run via background job IRL
		run_replace_bom_job(doc=log, boms=self.boms)
		log.reload()

		self.assertEqual(log.status, "Completed")


def update_cost_in_all_boms_in_test():
	"""
	Utility to run 'Update Cost' job in tests immediately without Cron job.
	Run job for all levels (manually) until fully complete.
	"""
	parent_boms = []
	log = enqueue_update_cost()  # create BOM Update Log

	while log.status != "Completed":
		level_boms, current_level = process_boms_cost_level_wise(log, parent_boms)
		log.reload()

		boms, batch = queue_bom_cost_jobs(
			level_boms, log, current_level
		)  # adds rows in log for tracking
		log.reload()

		update_cost_in_level(log, boms, batch)  # business logic
		log.reload()

		# current level done, get next level boms
		bom_batches = frappe.db.get_all(
			"BOM Update Batch",
			{"parent": log.name, "level": log.current_level},
			["name", "boms_updated", "status"],
		)
		current_boms, processed_boms = get_processed_current_boms(log, bom_batches)
		parent_boms = get_next_higher_level_boms(child_boms=current_boms, processed_boms=processed_boms)

		set_values_in_log(
			log.name,
			values={
				"processed_boms": json.dumps(processed_boms),
				"status": "Completed" if not parent_boms else "In Progress",
			},
		)
		log.reload()

	return log
