# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestWorkstationOperatingComponent(ERPNextTestSuite):
	def test_expense_account_validated(self):
		for account in ("Expenses - _TC", "Debtors - _TC", "Sales - _TC", "Cost of Goods Sold - _TC1"):
			component = make_component("_Test Component Bad Account", [("_Test Company", account)])
			self.assertRaises(frappe.ValidationError, component.insert)

		component = make_component(
			"_Test Component Good Account", [("_Test Company", "Cost of Goods Sold - _TC")]
		)
		component.insert()
		self.assertEqual(component.accounts[0].expense_account, "Cost of Goods Sold - _TC")


def make_component(name, accounts):
	return frappe.get_doc(
		{
			"doctype": "Workstation Operating Component",
			"component_name": name,
			"accounts": [{"company": company, "expense_account": account} for company, account in accounts],
		}
	)
