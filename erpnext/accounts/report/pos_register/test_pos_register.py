# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.report.pos_register.pos_register import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestPOSRegister(ERPNextTestSuite):
	def test_report_executes(self):
		# Smoke-guards the raw-SQL -> query-builder port: the report's POS Invoice query must
		# compile and run on both MariaDB and postgres (it returns columns + a row list either way).
		company = frappe.db.get_value("Company", {}, "name")
		columns, data = execute(
			frappe._dict({"company": company, "from_date": add_days(today(), -365), "to_date": today()})
		)
		self.assertTrue(columns)
		self.assertIsInstance(data, list)
