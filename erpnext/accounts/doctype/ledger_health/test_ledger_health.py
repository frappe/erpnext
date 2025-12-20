# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import qb
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.accounts.utils import run_ledger_health_checks


class TestLedgerHealth(AccountsTestMixin, IntegrationTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.configure_monitoring_tool()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def configure_monitoring_tool(self):
		monitor_settings = frappe.get_doc("Ledger Health Monitor")
		monitor_settings.enable_health_monitor = True
		monitor_settings.enable_for_last_x_days = 60
		monitor_settings.debit_credit_mismatch = True
		monitor_settings.general_and_payment_ledger_mismatch = True
		exists = [x for x in monitor_settings.companies if x.company == self.company]
		if not exists:
			monitor_settings.append("companies", {"company": self.company})
		monitor_settings.save()

	def clear_old_entries(self):
		super().clear_old_entries()
		lh = qb.DocType("Ledger Health")
		qb.from_(lh).delete().run()

	def create_journal(self):
		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.voucher_type = "Journal Entry"
		je.posting_date = nowdate()
		je.append(
			"accounts",
			{
				"account": self.debit_to,
				"party_type": "Customer",
				"party": self.customer,
				"debit_in_account_currency": 10000,
			},
		)
		je.append("accounts", {"account": self.income_account, "credit_in_account_currency": 10000})
		je.save().submit()
		self.je = je

	def test_debit_credit_mismatch(self):
		self.create_journal()

		# manually cause debit-credit mismatch
		gle = frappe.db.get_all(
			"GL Entry", filters={"voucher_no": self.je.name, "account": self.income_account}
		)[0]
		frappe.db.set_value("GL Entry", gle.name, "credit", 8000)

		run_ledger_health_checks()
		expected = {
			"voucher_type": self.je.doctype,
			"voucher_no": self.je.name,
			"debit_credit_mismatch": True,
			"general_and_payment_ledger_mismatch": False,
		}
		actual = frappe.db.get_all(
			"Ledger Health",
			fields=[
				"voucher_type",
				"voucher_no",
				"debit_credit_mismatch",
				"general_and_payment_ledger_mismatch",
			],
		)
		self.assertEqual(len(actual), 1)
		self.assertEqual(expected, actual[0])

	def test_gl_and_pl_mismatch(self):
		self.create_journal()

		# manually cause GL and PL discrepancy
		ple = frappe.db.get_all("Payment Ledger Entry", filters={"voucher_no": self.je.name})[0]
		frappe.db.set_value("Payment Ledger Entry", ple.name, "amount", 11000)

		run_ledger_health_checks()
		expected = {
			"voucher_type": self.je.doctype,
			"voucher_no": self.je.name,
			"debit_credit_mismatch": False,
			"general_and_payment_ledger_mismatch": True,
		}
		actual = frappe.db.get_all(
			"Ledger Health",
			fields=[
				"voucher_type",
				"voucher_no",
				"debit_credit_mismatch",
				"general_and_payment_ledger_mismatch",
			],
		)
		self.assertEqual(len(actual), 1)
		self.assertEqual(expected, actual[0])
