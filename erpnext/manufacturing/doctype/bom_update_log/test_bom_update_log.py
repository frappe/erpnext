# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.bom_update_log.bom_update_log import (
	BOMMissingError,
	run_bom_job,
)
from erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool import enqueue_replace_bom

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

		if self._testMethodName == "test_bom_update_log_completion":
			# clear logs and delete BOM created via setUp
			frappe.db.delete("BOM Update Log")
			self.new_bom_doc.cancel()
			self.new_bom_doc.delete()

			# explicitly commit and restore to original state
			frappe.db.commit()  # nosemgrep

	def test_bom_update_log_validate(self):
		"Test if BOM presence is validated."

		with self.assertRaises(BOMMissingError):
			enqueue_replace_bom(boms={})

		with self.assertRaises(frappe.ValidationError):
			enqueue_replace_bom(boms=frappe._dict(current_bom=self.boms.new_bom, new_bom=self.boms.new_bom))

		with self.assertRaises(frappe.ValidationError):
			enqueue_replace_bom(boms=frappe._dict(current_bom=self.boms.new_bom, new_bom="Dummy BOM"))

	def test_bom_update_log_queueing(self):
		"Test if BOM Update Log is created and queued."

		log = enqueue_replace_bom(
			boms=self.boms,
		)

		self.assertEqual(log.docstatus, 1)
		self.assertEqual(log.status, "Queued")

	def test_bom_update_log_completion(self):
		"Test if BOM Update Log handles job completion correctly."

		log = enqueue_replace_bom(
			boms=self.boms,
		)

		# Explicitly commits log, new bom (setUp) and replacement impact.
		# Is run via background jobs IRL
		run_bom_job(
			doc=log,
			boms=self.boms,
			update_type="Replace BOM",
		)
		log.reload()

		self.assertEqual(log.status, "Completed")

		# teardown (undo replace impact) due to commit
		boms = frappe._dict(
			current_bom=self.boms.new_bom,
			new_bom=self.boms.current_bom,
		)
		log2 = enqueue_replace_bom(
			boms=self.boms,
		)
		run_bom_job(  # Explicitly commits
			doc=log2,
			boms=boms,
			update_type="Replace BOM",
		)
		self.assertEqual(log2.status, "Completed")
