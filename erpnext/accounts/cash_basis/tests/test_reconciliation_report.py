# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Cash Basis Reconciliation (section 10) and invariant I5: the bridge ends at the cash net profit."""

import frappe
from frappe.tests.classes.context_managers import freeze_time
from frappe.utils import flt, fmt_money

from erpnext.accounts.cash_basis.calculation import get_exceptions
from erpnext.accounts.cash_basis.tests.fixtures import CUSTOMER, CUSTOMER_2, US_COMPANY, acc
from erpnext.accounts.cash_basis.tests.report_case import ReportTestCase, row_value
from erpnext.accounts.cash_basis.tests.vouchers import (
	line,
	make_advance,
	make_journal_entry,
	make_sales_invoice,
	pay,
	reconcile,
)
from erpnext.accounts.report.balance_sheet import balance_sheet
from erpnext.accounts.report.cash_basis_reconciliation import cash_basis_reconciliation
from erpnext.accounts.report.profit_and_loss_statement import profit_and_loss_statement
from erpnext.tests.utils import change_settings

TAX = acc("ST 6%")
DEBTORS = acc("Debtors")
YEAR = ("2026-01-01", "2026-12-31")


class TestCashBasisReconciliation(ReportTestCase):
	def reconciliation(self, from_date=YEAR[0], to_date=YEAR[1]):
		filters = frappe._dict(company=US_COMPANY, from_date=from_date, to_date=to_date)
		return cash_basis_reconciliation.execute(filters)[1]

	def line_value(self, data, label):
		return next(flt(row.get("amount"), 2) for row in data if label in str(row.get("description")))

	def net_profit(self, method, from_date=YEAR[0], to_date=YEAR[1]):
		result = self.run_report(
			profit_and_loss_statement.execute, from_date, to_date, accounting_method=method
		)
		return row_value(result, "account_name", "Profit for the year", key="total")

	def assert_bridge(self, from_date=YEAR[0], to_date=YEAR[1]):
		"""I5: accrual net profit plus the differences is the net profit of the cash basis P&L."""
		data = self.reconciliation(from_date, to_date)
		self.assertEqual(
			self.line_value(data, "Accrual net profit"), self.net_profit("Accrual", from_date, to_date)
		)
		self.assertEqual(
			self.line_value(data, "Cash net profit"), self.net_profit("Cash", from_date, to_date)
		)
		return data

	def test_bridge_for_part_payment(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		pay(invoice, "2026-04-10", 55)
		data = self.assert_bridge()
		self.assertEqual(self.line_value(data, "Accrual net profit"), 100)
		self.assertEqual(self.line_value(data, "unpaid convertible income"), -50)
		self.assertEqual(self.line_value(data, "Cash net profit"), 50)
		# Section 10.3: accrual retained earnings less cash retained earnings.
		self.assertEqual(self.line_value(data, "less cash retained earnings"), 50)

	def test_bridge_with_unapplied_cash(self):
		make_advance("Customer", CUSTOMER, "2026-02-10", 100)
		make_sales_invoice("2026-03-05", [line(100)])
		self.assert_bridge("2026-02-01", "2026-02-28")
		with freeze_time("2026-03-20"):
			reconcile("Customer", CUSTOMER, DEBTORS)
		data = self.assert_bridge("2026-02-01", "2026-02-28")
		self.assertEqual(self.line_value(data, "unapplied cash"), 100)
		self.assert_bridge("2026-03-01", "2026-03-31")

	def test_bridge_with_write_off(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		make_journal_entry(
			"2026-06-01",
			[
				{"account": acc("Write Off"), "debit": 110},
				{
					"account": DEBTORS,
					"credit": 110,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
				},
			],
			voucher_type="Write Off Entry",
		)
		data = self.assert_bridge()
		self.assertEqual(self.line_value(data, "non-cash settlements"), 100)
		self.assertEqual(self.line_value(data, "Cash net profit"), -10)

	def test_exceptions_are_listed_with_their_voucher(self):
		journal = make_journal_entry(
			"2026-03-01",
			[
				{"account": DEBTORS, "debit": 50, "party_type": "Customer", "party": CUSTOMER},
				{"account": DEBTORS, "debit": 50, "party_type": "Customer", "party": CUSTOMER_2},
				{"account": acc("Service"), "credit": 100},
			],
		)
		data = self.assert_bridge()
		rows = [row for row in data if row.get("voucher_no")]
		self.assertEqual(
			[(r["voucher_no"], r["description"]) for r in rows],
			[(journal.name, "Multiple parties")],
		)
		# The statements point to this report: the review line, and a Review button under it.
		result = self.run_report(profit_and_loss_statement.execute, *YEAR)
		self.assertIn('<p class="es-alert__description">1 voucher needs review', result[2])
		self.assertIn("reported when they are paid", result[2])
		self.assertIn('class="es-button es-alert__action" data-variant="outline"', result[2])
		self.assertIn("/desk/query-report/Cash%20Basis%20Reconciliation?company=", result[2])
		# The Balance Sheet adds its note to the line of the method, above the button.
		message = self.run_report(balance_sheet.execute, *YEAR, accumulated_values=1)[2]
		self.assertIn('data-variant="outline" data-size="md"', message)
		self.assertIn("reported when they are paid, and receivables and payables show only the tax", message)
		self.assertLess(message.index("receivables and payables"), message.index("es-alert__actions"))
		total = sum(flt(e["amount"]) for e in get_exceptions(US_COMPANY, YEAR[1]))
		self.assertIn(f"(total {fmt_money(total, currency='USD')})", result[2])

	def test_report_is_refused_with_no_country_in_scope(self):
		from unittest.mock import patch

		import erpnext.accounts.cash_basis as cash_basis

		with patch.object(cash_basis, "CASH_METHOD_COUNTRIES", ()):
			with self.assertRaisesRegex(frappe.ValidationError, "The cash basis is not available"):
				self.reconciliation()

	def test_company_outside_scope_is_refused(self):
		frappe.db.set_value("Company", US_COMPANY, "country", "Canada")
		self.assertRaises(frappe.ValidationError, self.reconciliation)

	def test_bridge_for_a_user_with_permission_limits(self):
		invoice = make_sales_invoice(
			"2026-03-01",
			[
				line(60, account=acc("Sales"), cost_center=acc("Main")),
				line(40, account=acc("Service"), cost_center=acc("Second")),
			],
		)
		pay(invoice, "2026-04-10", 50)
		user = "test-cash-basis-bridge@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Cash Basis Bridge",
					"roles": [{"role": "Accounts User"}, {"role": "Accounts Manager"}],
				}
			).insert()
		for allow, value in (("Company", US_COMPANY), ("Cost Center", acc("Main"))):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user,
					"allow": allow,
					"for_value": value,
					"apply_to_all_doctypes": 1,
				}
			).insert()
		with self.set_user(user):
			data = self.assert_bridge()
			self.assertEqual(self.line_value(data, "Cash net profit"), 30)
			self.assertTrue(any("needs access" in str(r.get("description")) for r in data))

	@change_settings("Accounts Settings", {"use_legacy_controller_for_pcv": 1})
	def test_bridge_across_a_period_closing(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": "2026-12-31",
				"period_start_date": "2026-01-01",
				"period_end_date": "2026-12-31",
				"company": US_COMPANY,
				"fiscal_year": frappe.db.get_value("Fiscal Year", {"year_start_date": "2026-01-01"}),
				"cost_center": acc("Main"),
				"closing_account_head": acc("Retained Earnings"),
				"remarks": "Cash basis test",
			}
		).insert().submit()
		pay(invoice, "2027-02-10")
		self.assert_bridge("2026-01-01", "2026-12-31")
		data = self.assert_bridge("2026-07-01", "2027-06-30")
		self.assertEqual(self.line_value(data, "Cash net profit"), 100)

	def test_bridge_with_a_finance_book(self):
		book = frappe.get_doc(
			{"doctype": "Finance Book", "finance_book_name": "_Test Cash Basis Bridge Book"}
		).insert()
		journal = make_journal_entry(
			"2026-03-01",
			[
				{"account": DEBTORS, "debit": 100, "party_type": "Customer", "party": CUSTOMER},
				{"account": acc("Service"), "credit": 100},
			],
			finance_book=book.name,
		)
		make_advance("Customer", CUSTOMER, "2026-04-10", 60, references=[("Journal Entry", journal.name, 60)])
		invoice = make_sales_invoice("2026-03-01", [line(50)])
		pay(invoice, "2026-04-10", 50)
		for extra in ({}, {"finance_book": book.name}):
			for include_default in (0, 1):
				filters = {**extra, "include_default_book_entries": include_default}
				data = cash_basis_reconciliation.execute(
					frappe._dict(company=US_COMPANY, from_date=YEAR[0], to_date=YEAR[1], **filters)
				)[1]
				result = self.run_report(profit_and_loss_statement.execute, *YEAR, **filters)
				profit = row_value(result, "account_name", "Profit for the year", key="total")
				self.assertEqual(self.line_value(data, "Cash net profit"), profit, filters)

	def test_bridge_with_revaluation(self):
		eur = acc("Debtors EUR")
		frappe.db.set_value(
			"Company",
			US_COMPANY,
			"unrealized_exchange_gain_loss_account",
			acc("Unrealized Exchange Gain/Loss"),
		)
		make_sales_invoice(
			"2026-03-01",
			[line(100)],
			customer="_Test Cash Basis EUR Customer",
			currency="EUR",
			conversion_rate=1.10,
			debit_to=eur,
			party_account_currency="EUR",
			ignore_pricing_rule=1,
		)
		revaluation = frappe.new_doc("Exchange Rate Revaluation")
		revaluation.update({"company": US_COMPANY, "posting_date": "2026-03-31"})
		revaluation.extend("accounts", revaluation.get_accounts_data())
		for row in revaluation.accounts:
			row.new_exchange_rate = 1.25
			row.new_balance_in_base_currency = row.new_exchange_rate * row.balance_in_account_currency
			row.gain_loss = row.new_balance_in_base_currency - row.balance_in_base_currency
		revaluation.set_total_gain_loss()
		revaluation.insert()
		revaluation.submit()
		frappe.get_doc("Journal Entry", revaluation.make_jv_entries().get("revaluation_jv")).submit()
		data = self.assert_bridge()
		self.assertEqual(self.line_value(data, "unrealised exchange differences"), -15)
		self.assertEqual(self.line_value(data, "Cash net profit"), 0)

	def test_message_with_two_exceptions(self):
		for _i in range(2):
			make_journal_entry(
				"2026-03-01",
				[
					{"account": DEBTORS, "debit": 50, "party_type": "Customer", "party": CUSTOMER},
					{"account": DEBTORS, "debit": 50, "party_type": "Customer", "party": CUSTOMER_2},
					{"account": acc("Service"), "credit": 100},
				],
			)
		message = self.run_report(profit_and_loss_statement.execute, *YEAR)[2]
		self.assertIn("2 vouchers need review", message)
		# The method is information, also when vouchers need review.
		self.assertIn('data-theme="blue"', message)
		self.assertIn("#icon-info-solid", message)
