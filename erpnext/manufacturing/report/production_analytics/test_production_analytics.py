# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_first_day, get_last_day, today


class TestProductionAnalytics(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, **extra):
		from erpnext.manufacturing.report.production_analytics.production_analytics import execute

		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": get_first_day(today()),
				"to_date": get_last_day(today()),
				"range": "Monthly",
			}
		)
		filters.update(extra)
		columns, data, _msg, _chart = execute(filters)
		return columns, data

	def get_period_count(self, columns, data, status, period_label):
		period_fieldname = next(col["fieldname"] for col in columns if col.get("label") == period_label)
		row = next(row for row in data if row["status"] == _(status))
		return row[period_fieldname]

	def test_counts_follow_user_permissions(self):
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record

		from_date, to_date = get_first_day(today()), get_last_day(today())
		user = create_user("production-analytics-user@example.com", "Manufacturing User")
		add_user_permission("Item", "_Test FG Item", user.name)

		def count():
			with self.set_user(user.name):
				columns, data = self.run_report(from_date=from_date, to_date=to_date)
			return self.get_period_count(columns, data, "Not Started", columns[-1]["label"])

		before = count()
		make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")
		make_wo_order_test_record(production_item="_Test FG Item 2", qty=10, company="_Test Company")

		self.assertEqual(count(), before + 1)
