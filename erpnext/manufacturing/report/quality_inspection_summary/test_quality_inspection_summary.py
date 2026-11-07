# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.manufacturing.report.quality_inspection_summary.quality_inspection_summary import execute
from erpnext.stock.doctype.quality_inspection.test_quality_inspection import (
	create_quality_inspection,
	make_minimal_job_card,
)


class TestQualityInspectionSummary(FrappeTestCase):
	def setUp(self):
		self.job_card = make_minimal_job_card(production_item="_Test Item")
		self.qi = create_quality_inspection(
			item_code="_Test Item",
			reference_type="Job Card",
			reference_name=self.job_card,
			status="Accepted",
		)

	def tearDown(self):
		frappe.db.rollback()

	def run_report_with_chart(self):
		filters = frappe._dict(from_date=add_days(nowdate(), -1), to_date=add_days(nowdate(), 1))
		_columns, data, _message, chart = execute(filters)
		return data, chart["data"]["datasets"][0]["values"]

	def test_draft_inspections_are_left_out(self):
		_data, before = self.run_report_with_chart()
		draft = create_quality_inspection(
			item_code="_Test Item",
			reference_type="Job Card",
			reference_name=self.job_card,
			do_not_submit=True,
		)

		data, after = self.run_report_with_chart()
		self.assertNotIn(draft.name, [row.name for row in data])
		self.assertEqual(after, before)

	def test_chart_counts_only_permitted_inspections(self):
		other = create_quality_inspection(
			item_code="_Test FG Item",
			reference_type="Job Card",
			reference_name=make_minimal_job_card(production_item="_Test FG Item"),
			status="Rejected",
		)
		user = create_user("quality-inspection-summary@example.com", "Quality Manager")
		add_user_permission("Item", "_Test Item", user.name)

		with self.set_user(user.name):
			data, chart = self.run_report_with_chart()

		self.assertIn(self.qi.name, [row.name for row in data])
		self.assertNotIn(other.name, [row.name for row in data])
		statuses = [row.status for row in data]
		self.assertEqual(chart, [statuses.count("Rejected"), statuses.count("Accepted")])
