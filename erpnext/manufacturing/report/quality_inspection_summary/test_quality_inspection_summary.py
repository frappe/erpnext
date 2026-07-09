# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.manufacturing.report.quality_inspection_summary.quality_inspection_summary import execute
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.quality_inspection.test_quality_inspection import (
	create_quality_inspection,
	make_minimal_job_card,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestQualityInspectionSummary(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		create_item("_Test Item")
		self.job_card = make_minimal_job_card(production_item="_Test Item")
		self.qi = create_quality_inspection(
			item_code="_Test Item",
			reference_type="Job Card",
			reference_name=self.job_card,
			status="Accepted",
		)

	def run_report(self, **extra):
		filters = frappe._dict(extra)
		return execute(filters)[1]

	def _rows_for_qi(self, data):
		return [row for row in data if row.get("name") == self.qi.name]

	def test_appears_in_date_range(self):
		data = self.run_report(from_date=add_days(nowdate(), -1), to_date=add_days(nowdate(), 1))
		rows = self._rows_for_qi(data)
		self.assertEqual(len(rows), 1)

		row = rows[0]
		self.assertEqual(row["status"], "Accepted")
		self.assertEqual(row["item_code"], "_Test Item")
		self.assertEqual(row["reference_type"], "Job Card")
		self.assertEqual(row["reference_name"], self.job_card)

	def test_excluded_outside_date_range(self):
		data = self.run_report(from_date=add_days(nowdate(), -10), to_date=add_days(nowdate(), -5))
		self.assertEqual(self._rows_for_qi(data), [])

	def test_status_filter_includes_matching(self):
		data = self.run_report(
			from_date=add_days(nowdate(), -1),
			to_date=add_days(nowdate(), 1),
			status=["Accepted"],
		)
		self.assertEqual(len(self._rows_for_qi(data)), 1)

	def test_status_filter_excludes_non_matching(self):
		data = self.run_report(
			from_date=add_days(nowdate(), -1),
			to_date=add_days(nowdate(), 1),
			status=["Rejected"],
		)
		self.assertEqual(self._rows_for_qi(data), [])

	def test_item_code_filter_includes_matching(self):
		data = self.run_report(
			from_date=add_days(nowdate(), -1),
			to_date=add_days(nowdate(), 1),
			item_code=["_Test Item"],
		)
		self.assertEqual(len(self._rows_for_qi(data)), 1)

	def test_item_code_filter_excludes_other_item(self):
		other_item = frappe.generate_hash(length=10)
		data = self.run_report(
			from_date=add_days(nowdate(), -1),
			to_date=add_days(nowdate(), 1),
			item_code=[other_item],
		)
		self.assertEqual(self._rows_for_qi(data), [])
