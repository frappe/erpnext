# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBudgetEntry(FrappeTestCase):
	def test_on_cancel_TC_BUD_001(self):
		"""Test the on_cancel() function by creating and cancelling a BudgetEntry"""

		# Step 1: Create and insert a fake "linked" Company doc
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "Test Budget Company",
				"abbr": "TBC",
				"default_currency": "INR",
			}
		)

		if not frappe.db.exists("Company", company.company_name):
			company.insert(ignore_permissions=True)

		# Step 2: Simulate a "submitted" linked doc in memory and re-save
		company.docstatus = 1
		company.save(ignore_permissions=True)

		# Step 3: Create and submit a BudgetEntry linked to this Company
		budget_entry = frappe.get_doc(
			{
				"doctype": "Budget Entry",
				"voucher_type": "Company",
				"voucher_no": company.name,
				"company": company.name,
				"overall_credit": 1000,
				"overall_debit": 500,
				"total": 1500,
			}
		)
		budget_entry.insert(ignore_permissions=True)
		budget_entry.submit()

		# Step 4: Try cancelling — this should raise frappe.ValidationError
		with self.assertRaises(frappe.ValidationError):
			budget_entry.cancel()
