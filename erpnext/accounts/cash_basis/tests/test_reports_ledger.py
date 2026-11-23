# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""General Ledger with the cash basis adjustment rows (phase 5)."""

import frappe
from frappe.utils import flt

from erpnext.accounts.cash_basis.tests.fixtures import US_COMPANY, acc, set_company_method
from erpnext.accounts.cash_basis.tests.report_case import ReportTestCase, comparable
from erpnext.accounts.cash_basis.tests.vouchers import (
	line,
	make_advance,
	make_journal_entry,
	make_sales_invoice,
	pay,
)
from erpnext.accounts.report.general_ledger import general_ledger
from erpnext.tests.utils import change_settings

SALES = acc("Sales")
DEBTORS = acc("Debtors")
TAX = acc("ST 6%")


class TestCashBasisGeneralLedger(ReportTestCase):
	def setUp(self):
		super().setUp()
		self.invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		self.payment = pay(self.invoice, "2026-04-10", 55)

	def ledger(self, from_date="2026-01-01", to_date="2026-12-31", **extra):
		filters = frappe._dict(
			company=US_COMPANY,
			from_date=from_date,
			to_date=to_date,
			**{"categorize_by": "Categorize by Voucher (Consolidated)", **extra},
		)
		return general_ledger.execute(filters)

	def closing(self, result):
		row = next(r for r in result[1] if r and "Closing" in str(r.get("account")))
		return flt(flt(row.get("debit")) - flt(row.get("credit")), 2)

	def test_ledger_rows_of_the_cash_basis(self):
		accrual = self.ledger(account=[SALES], accounting_method="Accrual", show_remarks=1)
		cash = self.ledger(account=[SALES], show_remarks=1)
		self.assertEqual(self.closing(accrual), -100)
		self.assertEqual(self.closing(cash), -50)
		remarks = {
			(r.get("voucher_no"), r.get("cash_basis_adjustment"))
			for r in cash[1]
			if r and r.get("cash_basis_adjustment")
		}
		self.assertEqual(
			remarks,
			{(self.invoice.name, "Deferred Until Paid"), (self.invoice.name, "Recognized When Paid")},
		)
		recognition = next(
			r for r in cash[1] if r and r.get("cash_basis_adjustment") == "Recognized When Paid"
		)
		self.assertEqual(str(recognition["posting_date"]), "2026-04-10")
		self.assertEqual(recognition["against_voucher"], self.payment.name)
		# The Remarks column keeps the remark of the voucher, as on its GL rows.
		invoice_remark = frappe.db.get_value("GL Entry", {"voucher_no": self.invoice.name}, "remarks")
		self.assertEqual(recognition["remarks"], invoice_remark)
		self.assertIn("cash_basis_adjustment", [c["fieldname"] for c in cash[0]])
		self.assertNotIn("cash_basis_adjustment", [c["fieldname"] for c in accrual[0]])

	def test_ledger_opening_on_the_cash_basis(self):
		cash = self.ledger(account=[SALES], from_date="2026-04-01")
		opening = next(r for r in cash[1] if r and "Opening" in str(r.get("account")))
		self.assertEqual(flt(opening.get("debit")) - flt(opening.get("credit")), 0)
		self.assertEqual(self.closing(cash), -50)

	def test_ledger_filters_apply_to_the_rows(self):
		cash = self.ledger(voucher_no=self.payment.name)
		self.assertFalse([r for r in cash[1] if r and bool(r.get("cash_basis_adjustment"))])
		by_party = self.ledger(party_type="Customer", party=[self.invoice.customer], account=[DEBTORS])
		# The receivable on the cash basis is the unpaid tax part: 5.
		self.assertEqual(self.closing(by_party), 5)

	def test_ledger_accrual_output_is_identical(self):
		set_company_method(US_COMPANY, "Accrual")
		before = comparable(self.ledger(account=[SALES]))
		set_company_method(US_COMPANY, "Cash")
		self.assertEqual(before, comparable(self.ledger(account=[SALES], accounting_method="Accrual")))

	def test_ledger_snapshot_falls_back_with_cash(self):
		filters = frappe._dict(
			company=US_COMPANY, from_date="2026-01-01", to_date="2026-12-31", account=[SALES]
		)
		self.assertEqual(self.closing(general_ledger.execute_snapshot_report(filters)), -50)

	def test_default_grouping_keeps_the_adjustment_rows_apart(self):
		result = self.ledger(account=[SALES], show_remarks=1)
		rows = [
			r
			for r in result[1]
			if r and r.get("voucher_no") == self.invoice.name and r.get("account") == SALES
		]
		amounts = sorted(
			(flt(r.get("debit")), flt(r.get("credit")), r.get("cash_basis_adjustment") or "") for r in rows
		)
		self.assertIn((0.0, 100.0, ""), amounts)
		self.assertIn((100.0, 0.0, "Deferred Until Paid"), amounts)

	def test_adjustment_row_comes_after_its_voucher(self):
		result = self.ledger(categorize_by="Categorize by Account", show_remarks=1)
		march = [
			r
			for r in result[1]
			if r and r.get("account") == SALES and str(r.get("posting_date")) == "2026-03-01"
		]
		self.assertEqual([bool(r.get("cash_basis_adjustment")) for r in march], [False, True])

	def test_against_voucher_filter_keeps_the_rows_of_the_obligation(self):
		result = self.ledger(account=[DEBTORS], against_voucher_no=self.invoice.name)
		self.assertEqual(self.closing(result), 5)

	def test_foreign_currency_receivable_in_its_own_currency(self):
		eur = acc("Debtors EUR")
		make_sales_invoice(
			"2026-05-01",
			[line(100)],
			customer="_Test Cash Basis EUR Customer",
			currency="EUR",
			conversion_rate=1.10,
			debit_to=eur,
			party_account_currency="EUR",
			ignore_pricing_rule=1,
		)
		result = self.ledger(account=[eur], show_remarks=1)
		deferral = next(r for r in result[1] if r and r.get("cash_basis_adjustment") == "Deferred Until Paid")
		self.assertEqual(deferral["account_currency"], "EUR")
		self.assertEqual(flt(deferral["credit_in_account_currency"]), 100)
		# One EUR account: the report shows EUR, the presentation currency of the account.
		self.assertEqual(flt(deferral["credit"]), 100)

	def test_journal_entry_with_two_rates_on_one_account(self):
		# Open point 10. 100 EUR at 1.10 and 100 EUR at 1.20, both for one customer: 230 USD.
		# The account currency of the deferral is 200 EUR, at the weighted rate, not the last.
		eur = acc("Debtors EUR")
		party = {"party_type": "Customer", "party": "_Test Cash Basis EUR Customer"}
		journal = make_journal_entry(
			"2026-05-01",
			[
				{"account": eur, "debit": 100, "exchange_rate": 1.10, **party},
				{"account": eur, "debit": 100, "exchange_rate": 1.20, **party},
				{"account": SALES, "credit": 230},
			],
			multi_currency=1,
		)
		result = self.ledger(account=[eur], from_date="2026-05-01")
		rows = [
			r
			for r in result[1]
			if r and r.get("cash_basis_adjustment") and r.get("voucher_no") == journal.name
		]
		self.assertTrue(rows)
		self.assertEqual(sum(flt(r["credit_in_account_currency"]) for r in rows), 200)

	def test_journal_entry_that_applies_a_foreign_currency_advance(self):
		# Review of batch 2. A Journal Entry moves an unapplied EUR advance of 100 to an invoice:
		# +100 EUR and -100 EUR for one customer on one account. The rows must not cancel in the
		# rate: the unapplied rows of the Journal Entry show 100 EUR, not 0.
		eur = acc("Debtors EUR")
		customer = "_Test Cash Basis EUR Customer"
		row_fields = {"party_type": "Customer", "party": customer, "exchange_rate": 1.10}
		advance = make_advance(
			"Customer",
			customer,
			"2026-05-01",
			100,
			party_account=eur,
			source_exchange_rate=1.10,
			received_amount=110,
		)
		invoice = make_sales_invoice(
			"2026-05-02",
			[line(100)],
			customer=customer,
			currency="EUR",
			conversion_rate=1.10,
			debit_to=eur,
			party_account_currency="EUR",
			ignore_pricing_rule=1,
		)
		journal = make_journal_entry(
			"2026-05-03",
			[
				{
					"account": eur,
					"debit": 100,
					"reference_type": "Payment Entry",
					"reference_name": advance.name,
					**row_fields,
				},
				{
					"account": eur,
					"credit": 100,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
					**row_fields,
				},
			],
			multi_currency=1,
		)
		result = self.ledger(account=[eur], from_date="2026-05-01")
		rows = [
			r
			for r in result[1]
			if r and r.get("cash_basis_adjustment") and r.get("voucher_no") == journal.name
		]
		self.assertTrue(rows)
		for row in rows:
			amount = flt(row["debit_in_account_currency"]) + flt(row["credit_in_account_currency"])
			self.assertEqual(amount, 100, row)

	def test_ledger_shows_the_message(self):
		self.assertIn("Accounting Method: Cash", self.ledger(account=[SALES])[2])

	def test_unapplied_rows_on_a_foreign_currency_account(self):
		eur = acc("Debtors EUR")
		payment = frappe.new_doc("Payment Entry")
		payment.update(
			{
				"company": US_COMPANY,
				"payment_type": "Receive",
				"party_type": "Customer",
				"party": "_Test Cash Basis EUR Customer",
				"posting_date": "2026-02-10",
				"paid_from": eur,
				"paid_from_account_currency": "EUR",
				"paid_to": acc("Test Bank"),
				"paid_to_account_currency": "USD",
				"paid_amount": 100,
				"source_exchange_rate": 1.20,
				"received_amount": 120,
				"target_exchange_rate": 1,
				"reference_no": "EUR-ADV",
				"reference_date": "2026-02-10",
			}
		)
		payment.insert()
		payment.submit()
		result = self.ledger(account=[eur], show_remarks=1)
		unapplied = next(r for r in result[1] if r and r.get("cash_basis_adjustment") == "Unapplied Cash")
		# The receipt of 100 EUR goes off the receivable onto the unapplied account: 100 EUR, 120 USD.
		self.assertEqual(unapplied["account_currency"], "EUR")
		self.assertEqual(flt(unapplied["debit_in_account_currency"]), 100)

	def test_revaluation_row_has_no_amount_in_account_currency(self):
		eur = acc("Debtors EUR")
		frappe.db.set_value(
			"Company",
			US_COMPANY,
			"unrealized_exchange_gain_loss_account",
			acc("Unrealized Exchange Gain/Loss"),
		)
		make_sales_invoice(
			"2026-05-01",
			[line(100)],
			customer="_Test Cash Basis EUR Customer",
			currency="EUR",
			conversion_rate=1.10,
			debit_to=eur,
			party_account_currency="EUR",
			ignore_pricing_rule=1,
		)
		revaluation = frappe.new_doc("Exchange Rate Revaluation")
		revaluation.update({"company": US_COMPANY, "posting_date": "2026-05-31"})
		revaluation.extend("accounts", revaluation.get_accounts_data())
		for row in revaluation.accounts:
			row.new_exchange_rate = 1.25
			row.new_balance_in_base_currency = row.new_exchange_rate * row.balance_in_account_currency
			row.gain_loss = row.new_balance_in_base_currency - row.balance_in_base_currency
		revaluation.set_total_gain_loss()
		revaluation.insert()
		revaluation.submit()
		frappe.get_doc("Journal Entry", revaluation.make_jv_entries().get("revaluation_jv")).submit()
		result = self.ledger(account=[eur], show_remarks=1)
		rows = [r for r in result[1] if r and r.get("cash_basis_adjustment") == "Exchange Difference Removed"]
		self.assertTrue(rows)
		for row in rows:
			self.assertEqual(
				flt(row["debit_in_account_currency"]) + flt(row["credit_in_account_currency"]), 0
			)

	def test_order_of_accounts_follows_the_database(self):
		# "IT" and "In" sort one way in Python and another way in a case-insensitive collation.
		accounts = []
		for name in ("Insurance Income", "IT Income"):
			accounts.append(
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": name,
						"parent_account": acc("Direct Income"),
						"company": US_COMPANY,
					}
				)
				.insert()
				.name
			)
		for day, account in (
			("2026-02-01", accounts[1]),
			("2026-06-01", accounts[1]),
			("2026-03-01", accounts[0]),
		):
			invoice = make_sales_invoice(day, [line(10, account=account)])
			pay(invoice, day)
		make_sales_invoice("2026-05-01", [line(10, account=accounts[1])])
		result = self.ledger(categorize_by="Categorize by Account")
		it_rows = [r for r in result[1] if r and r.get("account") == accounts[1] and r.get("posting_date")]
		dates = [str(r["posting_date"]) for r in it_rows]
		self.assertEqual(dates, sorted(dates), "the rows of one account stay in date order")

	def test_categorize_by_voucher_keeps_the_sql_order(self):
		first = make_sales_invoice("2026-01-05", [line(10)])
		pay(first, "2026-01-05")
		make_journal_entry(
			"2026-01-06",
			[{"account": acc("Test Bank"), "debit": 5}, {"account": acc("Capital Stock"), "credit": 5}],
		)
		second = make_sales_invoice("2026-01-06", [line(20)])
		result = self.ledger(to_date="2026-01-31", categorize_by="Categorize by Voucher", show_remarks=1)
		day = [r for r in result[1] if r and str(r.get("posting_date")) == "2026-01-06"]
		types = [r["voucher_type"] for r in day]
		self.assertEqual(types, sorted(types), "the voucher types of one date follow the SQL order")
		rows_of_second = [r for r in day if r.get("voucher_no") == second.name]
		self.assertEqual(rows_of_second[-1].get("cash_basis_adjustment"), "Deferred Until Paid")

	def test_default_view_keeps_dates_in_order(self):
		result = self.ledger(categorize_by="", show_remarks=1)
		dates = [str(r["posting_date"]) for r in result[1] if r and r.get("posting_date")]
		self.assertEqual(dates, sorted(dates))
		recognition = next(
			r for r in result[1] if r and r.get("cash_basis_adjustment") == "Recognized When Paid"
		)
		self.assertEqual(str(recognition["posting_date"]), "2026-04-10")

	@change_settings("Accounts Settings", {"general_ledger_remarks_length": 5})
	def test_remarks_of_adjustment_rows_follow_the_length_setting(self):
		frappe.db.set_value("GL Entry", {"voucher_no": self.invoice.name}, "remarks", "Paid in two parts")
		result = self.ledger(account=[SALES], show_remarks=1)
		remarks = {
			r.get("remarks")
			for r in result[1]
			if r and r.get("cash_basis_adjustment") and r.get("voucher_no") == self.invoice.name
		}
		# The General Ledger cuts the remark to 5 characters: "Paid ".
		self.assertEqual(remarks, {"Paid "})

	def test_remark_of_adjustment_rows_is_the_remark_of_the_first_gl_row(self):
		# When the GL rows of a voucher have different remarks, the adjustment rows take the remark
		# of the first row. "Max" took "Zeta", the largest text.
		rows = frappe.get_all(
			"GL Entry", {"voucher_no": self.invoice.name}, pluck="name", order_by="creation, name"
		)
		frappe.db.set_value("GL Entry", {"name": ("in", rows[1:])}, "remarks", "Zeta row")
		frappe.db.set_value("GL Entry", rows[0], "remarks", "Alpha row")
		result = self.ledger(account=[SALES], show_remarks=1)
		remarks = {
			r.get("remarks")
			for r in result[1]
			if r and r.get("cash_basis_adjustment") and r.get("voucher_no") == self.invoice.name
		}
		self.assertEqual(remarks, {"Alpha row"})

	def test_statement_of_account_prints_the_accrual_balance(self):
		# A statement shows what the customer owes: 110 invoiced, 55 paid, 55 owed. The cash
		# basis General Ledger of the customer closes at 5 (the tax of the unpaid half).
		from frappe.utils.print_format import render_report_jinja

		from erpnext.accounts.cash_basis.reports import get_statement_print_rows

		party = {"party_type": "Customer", "party": [self.invoice.customer], "account": [DEBTORS]}
		cash = self.ledger(**party)
		self.assertEqual(self.closing(cash), 5)
		filters = self.print_filters(**party)
		rows, method = get_statement_print_rows(filters, cash[1])
		self.assertEqual((self.closing((None, rows)), method), (55, None))
		self.assertFalse([r for r in rows if r and r.get("cash_basis_adjustment")])
		html = render_report_jinja("Statement of Account", data=cash[1], filters=filters, no_letterhead=1)[
			"body"
		]
		self.assertIn("55.00 Dr", html)
		# On the accrual basis the rows of the run stay as they are.
		accrual_rows = self.ledger(accounting_method="Accrual", **party)[1]
		accrual = {**filters, "accounting_method": "Accrual"}
		self.assertEqual(get_statement_print_rows(accrual, accrual_rows), (accrual_rows, None))

	def test_account_ledger_print_keeps_the_cash_rows(self):
		# The same format prints an account ledger. It is not a statement, so it keeps the cash
		# basis rows of the run and shows the method: Sales closes at 50 on cash, 100 on accrual.
		from frappe.utils.print_format import render_report_jinja

		from erpnext.accounts.cash_basis.reports import get_statement_print_rows

		cash = self.ledger(account=[SALES])
		filters = self.print_filters(account=[SALES])
		self.assertEqual(get_statement_print_rows(filters, cash[1]), (cash[1], "Cash"))
		html = render_report_jinja("Statement of Account", data=cash[1], filters=filters, no_letterhead=1)[
			"body"
		]
		self.assertIn("Accounting Method: Cash", html)
		self.assertIn("Cash Basis Adjustment", html)

	def print_filters(self, **extra):
		return {
			"company": US_COMPANY,
			"from_date": "2026-01-01",
			"to_date": "2026-12-31",
			"categorize_by": "Categorize by Voucher (Consolidated)",
			"accounting_method": "Cash",
			**extra,
		}
