# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import qb
from frappe.tests.classes.context_managers import freeze_time
from frappe.utils import add_days, now_datetime, nowdate

from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.accounts.utils import run_ledger_health_checks
from erpnext.tests.utils import ERPNextTestSuite


class TestLedgerHealth(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.company = "_Test Company"
		self.customer = "_Test Customer"
		self.debit_to = "Debtors - _TC"
		self.income_account = "Sales - _TC"
		self.configure_monitoring_tool()

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

	def create_journal(self, posting_date=None):
		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.voucher_type = "Journal Entry"
		je.posting_date = posting_date or nowdate()
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

	def get_ledger_health_rows(self):
		return frappe.db.get_all(
			"Ledger Health",
			fields=[
				"voucher_type",
				"voucher_no",
				"debit_credit_mismatch",
				"general_and_payment_ledger_mismatch",
			],
		)

	def test_gl_and_pl_mismatch_in_account_currency(self):
		self.create_journal()
		frappe.db.set_value(
			"Payment Ledger Entry", {"voucher_no": self.je.name}, "amount_in_account_currency", 9000
		)

		run_ledger_health_checks()

		self.assertEqual(
			self.get_ledger_health_rows(),
			[
				{
					"voucher_type": self.je.doctype,
					"voucher_no": self.je.name,
					"debit_credit_mismatch": False,
					"general_and_payment_ledger_mismatch": True,
				}
			],
		)

	def test_mismatch_recorded_once_and_cleared_after_fix(self):
		self.create_journal()
		gle = frappe.db.get_value("GL Entry", {"voucher_no": self.je.name, "account": self.income_account})
		frappe.db.set_value("GL Entry", gle, "credit", 9000)

		run_ledger_health_checks()
		first_check = frappe.db.get_value(
			"Ledger Health", {"voucher_no": self.je.name}, ["name", "checked_on"]
		)
		run_ledger_health_checks()

		rows = frappe.db.get_all("Ledger Health", fields=["name", "checked_on"])
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].name, first_check[0])
		self.assertGreater(rows[0].checked_on, first_check[1])

		frappe.db.set_value("GL Entry", gle, "credit", 10000)
		run_ledger_health_checks()
		self.assertEqual(self.get_ledger_health_rows(), [])

	def record_unbalanced_journal(self, posting_date=None):
		self.create_journal(posting_date)
		gle = frappe.db.get_value("GL Entry", {"voucher_no": self.je.name, "account": self.income_account})
		frappe.db.set_value("GL Entry", gle, "credit", 9000)
		run_ledger_health_checks()
		self.assertEqual(len(self.get_ledger_health_rows()), 1)

	def test_mismatch_outside_monitored_days_is_kept(self):
		frappe.db.set_single_value("Ledger Health Monitor", "monitor_for_last_x_days", 120)
		self.record_unbalanced_journal(posting_date=add_days(nowdate(), -90))

		frappe.db.set_single_value("Ledger Health Monitor", "monitor_for_last_x_days", 60)
		run_ledger_health_checks()
		self.assertEqual(len(self.get_ledger_health_rows()), 1)

	def test_mismatch_kept_when_no_company_is_monitored(self):
		self.record_unbalanced_journal()

		monitor_settings = frappe.get_doc("Ledger Health Monitor")
		monitor_settings.companies = []
		monitor_settings.save()
		run_ledger_health_checks()
		self.assertEqual(len(self.get_ledger_health_rows()), 1)

	def test_duplicate_records_collapse_to_oldest(self):
		self.create_journal()
		gle = frappe.db.get_value("GL Entry", {"voucher_no": self.je.name, "account": self.income_account})
		frappe.db.set_value("GL Entry", gle, "credit", 9000)
		names = []
		for _record in range(2):
			doc = frappe.new_doc("Ledger Health")
			doc.update(
				{
					"voucher_type": self.je.doctype,
					"voucher_no": self.je.name,
					"debit_credit_mismatch": 1,
					"checked_on": add_days(now_datetime(), -1),
				}
			)
			names.append(doc.save().name)

		run_time = now_datetime().replace(microsecond=0)
		with freeze_time(run_time):
			run_ledger_health_checks()

		rows = frappe.db.get_all("Ledger Health", fields=["name", "checked_on"])
		self.assertEqual(rows, [{"name": min(names), "checked_on": run_time}])
