# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.controllers.stock_controller import (
	show_accounting_ledger_preview,
	show_stock_ledger_preview,
)
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestLedgerPreviewPermission(ERPNextTestSuite):
	def test_accounting_ledger_preview_requires_read_permission(self):
		company = "_Test Company"
		je = make_journal_entry("_Test Cash - _TC", "_Test Bank - _TC", 100, submit=True)

		email = "ledger_preview_no_role@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "No Role",
					"user_type": "Website User",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		try:
			frappe.set_user(email)
			self.assertRaises(
				frappe.PermissionError,
				show_accounting_ledger_preview,
				company,
				"Journal Entry",
				je.name,
			)
		finally:
			frappe.set_user("Administrator")

		# a permitted user is still able to read the preview
		accounting_ledger_result = show_accounting_ledger_preview(company, "Journal Entry", je.name)
		self.assertTrue(accounting_ledger_result.get("gl_data"))

	def test_stock_ledger_preview_requires_read_permission(self):
		company = "_Test Company"
		pr = make_purchase_receipt()

		email = "ledger_preview_no_role@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "No Role",
					"user_type": "Website User",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		try:
			frappe.set_user(email)
			self.assertRaises(
				frappe.PermissionError,
				show_stock_ledger_preview,
				company,
				"Purchase Receipt",
				pr.name,
			)
		finally:
			frappe.set_user("Administrator")

		stock_ledger_result = show_stock_ledger_preview(company, "Purchase Receipt", pr.name)
		self.assertTrue(stock_ledger_result.get("sl_data"))
