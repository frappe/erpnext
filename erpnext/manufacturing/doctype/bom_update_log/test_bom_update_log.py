# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.manufacturing.doctype.bom_update_log.bom_update_log import (
	BOMMissingError,
	resume_bom_cost_update_jobs,
)
from erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool import (
	enqueue_replace_bom,
	enqueue_update_cost,
)

EXTRA_TEST_RECORD_DEPENDENCIES = ["BOM"]


class TestBOMUpdateLog(IntegrationTestCase):
	"Test BOM Update Tool Operations via BOM Update Log."

	def setUp(self):
		bom_doc = frappe.copy_doc(self.globalTestRecords["BOM"][0])
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

	def test_bom_update_log_completion(self):
		"Test if BOM Update Log handles job completion correctly."

		log = enqueue_replace_bom(boms=self.boms)
		log.reload()
		self.assertEqual(log.status, "Completed")

	def test_bom_replace_for_root_bom(self):
		"""
		- B-Item A (Root Item)
		        - B-Item B
		                - B-Item C
		        - B-Item D
		                - B-Item E
		                        - B-Item F

		Create New BOM for B-Item E with B-Item G and replace it in the above BOM.
		"""

		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom
		from erpnext.stock.doctype.item.test_item import make_item

		items = ["B-Item A", "B-Item B", "B-Item C", "B-Item D", "B-Item E", "B-Item F", "B-Item G"]

		for item_code in items:
			if not frappe.db.exists("Item", item_code):
				make_item(item_code)

		for item_code in items:
			remove_bom(item_code)

		bom_tree = {"B-Item A": {"B-Item B": {"B-Item C": {}}, "B-Item D": {"B-Item E": {"B-Item F": {}}}}}

		root_bom = create_nested_bom(bom_tree, prefix="")

		exploded_items = frappe.get_all(
			"BOM Explosion Item", filters={"parent": root_bom.name}, fields=["item_code"]
		)

		exploded_items = [item.item_code for item in exploded_items]
		expected_exploded_items = ["B-Item C", "B-Item F"]
		self.assertEqual(sorted(exploded_items), sorted(expected_exploded_items))

		old_bom = frappe.db.get_value("BOM", {"item": "B-Item E"}, "name")
		bom_tree = {"B-Item E": {"B-Item G": {}}}

		new_bom = create_nested_bom(bom_tree, prefix="")
		enqueue_replace_bom(boms=frappe._dict(current_bom=old_bom, new_bom=new_bom.name))

		exploded_items = frappe.get_all(
			"BOM Explosion Item", filters={"parent": root_bom.name}, fields=["item_code"]
		)

		exploded_items = [item.item_code for item in exploded_items]
		expected_exploded_items = ["B-Item C", "B-Item G"]
		self.assertEqual(sorted(exploded_items), sorted(expected_exploded_items))


def remove_bom(item_code):
	boms = frappe.get_all("BOM", fields=["docstatus", "name"], filters={"item": item_code})

	for row in boms:
		if row.docstatus == 1:
			frappe.get_doc("BOM", row.name).cancel()

		frappe.delete_doc("BOM", row.name)


def update_cost_in_all_boms_in_test():
	"""
	Utility to run 'Update Cost' job in tests without Cron job until fully complete.
	"""
	log = enqueue_update_cost()  # create BOM Update Log

	while log.status != "Completed":
		resume_bom_cost_update_jobs()  # run cron job until complete
		log.reload()

	return log
