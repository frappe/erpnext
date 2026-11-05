# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
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
