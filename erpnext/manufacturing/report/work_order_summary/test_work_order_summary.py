# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.work_order_summary.work_order_summary import execute


class TestWorkOrderSummary(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": add_days(today(), -1),
				"to_date": today(),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_work_order_planned_for_later_is_listed(self):
		wo = make_wo_order_test_record(
			production_item="_Test FG Item",
			qty=10,
			company="_Test Company",
			planned_start_date=add_days(today(), 5),
		)

		rows = {row["name"]: row for row in self.run_report(to_date=add_days(today(), 30))}

		self.assertIn(wo.name, rows)
		self.assertEqual(rows[wo.name]["age"], 0)
