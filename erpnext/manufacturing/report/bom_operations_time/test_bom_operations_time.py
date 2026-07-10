# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.report.bom_operations_time.bom_operations_time import execute
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

OPERATION = "_Test BOM Ops Time Operation"
WORKSTATION = "_Test BOM Ops Time Workstation"
OTHER_OPERATION = "_Test BOM Ops Time Operation 2"
OTHER_WORKSTATION = "_Test BOM Ops Time Workstation 2"
TIME_IN_MINS = 45


class TestBOMOperationsTime(ERPNextTestSuite):
	def setUp(self):
		ensure_workstation_and_operation(WORKSTATION, OPERATION)
		self.rm_item = make_item(properties={"is_stock_item": 1, "valuation_rate": 100}).name
		self.fg_item = make_item(properties={"is_stock_item": 1}).name
		self.bom = build_bom_with_operation(self.fg_item, self.rm_item, OPERATION, WORKSTATION)

	def run_report(self, **filters):
		return execute(frappe._dict(filters))[1]

	def bom_names(self, rows):
		return {row.name for row in rows}

	def build_other_bom(self):
		"""A submitted BOM for a different item, built on a different workstation."""
		ensure_workstation_and_operation(OTHER_WORKSTATION, OTHER_OPERATION)
		other_fg = make_item(properties={"is_stock_item": 1}).name
		return build_bom_with_operation(other_fg, self.rm_item, OTHER_OPERATION, OTHER_WORKSTATION)

	def test_operation_row_appears_with_expected_values(self):
		rows = self.run_report(bom_id=[self.bom.name])

		self.assertEqual(len(rows), 1)
		row = rows[0]
		self.assertEqual(row.name, self.bom.name)
		self.assertEqual(row.item, self.fg_item)
		self.assertEqual(row.operation, OPERATION)
		self.assertEqual(row.workstation, WORKSTATION)
		self.assertEqual(row.time_in_mins, TIME_IN_MINS)

	def test_item_code_filter_includes_matching_and_excludes_other(self):
		other_bom = self.build_other_bom()

		# no bom_id here, so the item_code filter alone must scope the result
		names = self.bom_names(self.run_report(item_code=self.fg_item))
		self.assertIn(self.bom.name, names)
		self.assertNotIn(other_bom.name, names)

		# reverse direction: filtering the other item drops our BOM
		other_names = self.bom_names(self.run_report(item_code=other_bom.item))
		self.assertIn(other_bom.name, other_names)
		self.assertNotIn(self.bom.name, other_names)

	def test_workstation_filter_includes_matching_and_excludes_other(self):
		other_bom = self.build_other_bom()

		# no bom_id here, so the workstation filter alone must scope the result
		names = self.bom_names(self.run_report(workstation=WORKSTATION))
		self.assertIn(self.bom.name, names)
		self.assertNotIn(other_bom.name, names)

		# reverse direction: filtering the other workstation drops our BOM
		other_names = self.bom_names(self.run_report(workstation=OTHER_WORKSTATION))
		self.assertIn(other_bom.name, other_names)
		self.assertNotIn(self.bom.name, other_names)

	def test_draft_bom_excluded(self):
		draft_bom = build_bom_with_operation(
			make_item(properties={"is_stock_item": 1}).name,
			self.rm_item,
			OPERATION,
			WORKSTATION,
			do_not_submit=True,
		)

		rows = self.run_report(bom_id=[draft_bom.name])
		self.assertEqual(rows, [])


def ensure_workstation_and_operation(workstation, operation):
	if not frappe.db.exists("Workstation", workstation):
		frappe.get_doc({"doctype": "Workstation", "workstation_name": workstation}).insert(
			ignore_permissions=True
		)

	if not frappe.db.exists("Operation", operation):
		frappe.get_doc({"doctype": "Operation", "name": operation, "workstation": workstation}).insert(
			ignore_permissions=True
		)


def build_bom_with_operation(fg_item, rm_item, operation, workstation, do_not_submit=False):
	bom = make_bom(
		item=fg_item,
		raw_materials=[rm_item],
		with_operations=1,
		do_not_save=True,
	)
	bom.append(
		"operations",
		{
			"operation": operation,
			"workstation": workstation,
			"time_in_mins": TIME_IN_MINS,
			"hour_rate": 100,
		},
	)
	bom.insert(ignore_permissions=True)
	if not do_not_submit:
		bom.submit()
	return bom
