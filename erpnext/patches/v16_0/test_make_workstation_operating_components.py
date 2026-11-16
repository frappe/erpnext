# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.patches.v16_0 import make_workstation_operating_components
from erpnext.tests.utils import ERPNextTestSuite

COMPONENTS = ("Electricity", "Consumables", "Rent", "Wages")


class TestMakeWorkstationOperatingComponents(ERPNextTestSuite):
	def test_skips_default_account_that_is_not_an_expense_account(self):
		frappe.db.delete("Workstation Operating Component", {"name": ("in", COMPONENTS)})
		frappe.db.set_value(
			"Company",
			"_Test Company",
			{"default_operating_cost_account": None, "default_expense_account": "Stock In Hand - _TC"},
		)

		make_workstation_operating_components.execute()

		for component in COMPONENTS:
			doc = frappe.get_doc("Workstation Operating Component", component)
			test_company_row = next(row for row in doc.accounts if row.company == "_Test Company")
			self.assertIsNone(test_company_row.expense_account)
