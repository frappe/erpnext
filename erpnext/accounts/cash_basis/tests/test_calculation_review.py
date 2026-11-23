# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Points of the functional review of the calculation (PR_SERIES.md, section 5D)."""

import frappe
from frappe.utils import flt

from erpnext.accounts.cash_basis.calculation import get_exceptions
from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import (
	CUSTOMER,
	CUSTOMER_2,
	EUR_CUSTOMER,
	SUPPLIER,
	TEST_UNAPPLIED_PAYMENTS,
	US_COMPANY,
	acc,
)
from erpnext.accounts.cash_basis.tests.vouchers import (
	BANK,
	line,
	make_advance,
	make_journal_entry,
	make_sales_invoice,
	pay,
)

SALES = acc("Sales")
DEBTORS = acc("Debtors")
CREDITORS = acc("Creditors")
WRITE_OFF = acc("Write Off")


def get_employee() -> str:
	name = frappe.db.get_value("Employee", {"first_name": "_Test Cash Basis", "company": US_COMPANY})
	if name:
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "_Test Cash Basis",
				"gender": frappe.db.get_value("Gender", {}) or "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"company": US_COMPANY,
			}
		)
		.insert()
		.name
	)


def settle(invoice, amount):
	return {
		"account": DEBTORS,
		"credit": amount,
		"party_type": "Customer",
		"party": CUSTOMER,
		"reference_type": "Sales Invoice",
		"reference_name": invoice.name,
	}


class TestCashBasisReviewPoints(CashBasisTestCase):
	def test_party_only_journal_with_an_employee_row(self):
		# 5D point 3. A supplier advance of 100, then a Journal Entry with only party rows moves
		# it to an employee. Only customers and suppliers convert, so the employee row is left out.
		make_advance("Supplier", SUPPLIER, "2026-02-10", 100)
		make_journal_entry(
			"2026-03-01",
			[
				{"account": CREDITORS, "credit": 100, "party_type": "Supplier", "party": SUPPLIER},
				{"account": CREDITORS, "debit": 100, "party_type": "Employee", "party": get_employee()},
			],
		)
		rows = self.adjustments("2026-03-31")
		self.assertFalse([r for r in rows if r.get("party_type") == "Employee"])
		# The advance is an unapplied payment of 100 in February. The Journal Entry draws it
		# from the supplier on 1 March, so the unapplied account is 0 again at the end of March.
		self.assert_balances("2026-02-28", cash={TEST_UNAPPLIED_PAYMENTS: 100})
		self.assert_balances("2026-03-31", cash={TEST_UNAPPLIED_PAYMENTS: 0})
		self.assert_invariants("2026-03-31")

	def test_voucher_with_no_gl_rows_fails_the_proof_rule(self):
		# 5D point 6. A PLE row with no GL row cannot be checked.
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		frappe.db.delete("GL Entry", {"voucher_no": invoice.name})
		self.assertEqual(self.exception_reasons(), {invoice.name: "proof rule failed"})

	def test_mixed_settlement_of_two_invoices_lists_the_total(self):
		# 5D point 7. One Journal Entry settles 100 and 50, with a bank row and a write-off row.
		first = make_sales_invoice("2026-03-01", [line(100)])
		second = make_sales_invoice("2026-03-02", [line(50)])
		journal = make_journal_entry(
			"2026-04-10",
			[
				settle(first, 100),
				settle(second, 50),
				{"account": BANK, "debit": 140},
				{"account": WRITE_OFF, "debit": 10},
			],
		)
		listed = [e for e in get_exceptions(US_COMPANY, "2026-12-31") if e["voucher_no"] == journal.name]
		self.assertEqual([(e["reason"], flt(e["amount"])) for e in listed], [("mixed settlement", 150)])

	def test_non_cash_adjustment_with_a_transfer_to_another_party(self):
		# 5D point 4: no fault. A credits 100: 60 moves to B, 40 is written off. The ratio of the
		# settler uses the net of the party rows (-40), so the removal is the write-off of 40.
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		journal = make_journal_entry(
			"2026-04-10",
			[
				settle(invoice, 100),
				{"account": DEBTORS, "debit": 60, "party_type": "Customer", "party": CUSTOMER_2},
				{"account": WRITE_OFF, "debit": 40},
			],
			cash_basis_treatment="Non-cash Adjustment",
		)
		# The Journal Entry also has its own row for B, with two parties: an exception.
		self.assertEqual(self.exception_reasons()[journal.name], "multiple parties")
		self.assert_balances(
			"2026-04-30",
			accrual={SALES: -100, WRITE_OFF: 40},
			cash={SALES: 0, WRITE_OFF: 0},
		)

	def test_mixed_settlement_in_two_currencies_is_in_company_currency(self):
		# 5D point 7, review: 100 EUR at 1.10 (110 USD) and 50 USD, settled by one Journal Entry
		# with a bank row and a write-off row. The exception is 160 USD, with no single party.
		eur_invoice = make_sales_invoice(
			"2026-03-01",
			[line(100)],
			customer=EUR_CUSTOMER,
			currency="EUR",
			conversion_rate=1.10,
			debit_to=acc("Debtors EUR"),
			party_account_currency="EUR",
			ignore_pricing_rule=1,
		)
		usd_invoice = make_sales_invoice("2026-03-02", [line(50)])
		journal = make_journal_entry(
			"2026-04-10",
			[
				{
					"account": acc("Debtors EUR"),
					"credit": 100,
					"exchange_rate": 1.10,
					"party_type": "Customer",
					"party": EUR_CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": eur_invoice.name,
				},
				settle(usd_invoice, 50),
				{"account": BANK, "debit": 150},
				{"account": WRITE_OFF, "debit": 10},
			],
			multi_currency=1,
		)
		listed = [e for e in get_exceptions(US_COMPANY, "2026-12-31") if e["voucher_no"] == journal.name]
		self.assertEqual(
			[(e["reason"], flt(e["amount"]), e["party"]) for e in listed], [("mixed settlement", 160, None)]
		)

	def test_settler_of_another_voucher_type_keeps_its_date(self):
		# 5D point 1. The calculation loads the dates of invoices, Payment Entries and Journal
		# Entries. A settling voucher of another type takes the date of its ledger row, not today.
		from erpnext.accounts.cash_basis.settlements import get_settlement_events

		invoice = make_sales_invoice("2026-03-01", [line(100)])
		payment = pay(invoice, "2026-04-10")
		frappe.db.set_value(
			"Payment Ledger Entry", {"voucher_no": payment.name}, "voucher_type", "Bank Transaction"
		)
		listed = [e for e in get_exceptions(US_COMPANY, "2026-12-31") if e["voucher_no"] == payment.name]
		self.assertEqual(
			[(e["reason"], str(e["posting_date"])) for e in listed], [("mixed settlement", "2026-04-10")]
		)
		events = [
			e for e in get_settlement_events(US_COMPANY, "2026-12-31") if e["voucher_no"] == payment.name
		]
		self.assertEqual([str(e["recognition_date"]) for e in events], ["2026-04-10"])

	def test_self_settlement_in_a_foreign_currency_has_its_company_amount(self):
		# Open point 23. A EUR POS invoice of 100 at 1.10: 90 EUR paid in cash, 10 EUR written off.
		# Each self-settlement event has its account currency amount and its company amount.
		from erpnext.accounts.cash_basis.settlements import get_settlement_events

		invoice = make_sales_invoice(
			"2026-03-01",
			[line(100)],
			customer=EUR_CUSTOMER,
			currency="EUR",
			conversion_rate=1.10,
			debit_to=acc("Debtors EUR"),
			party_account_currency="EUR",
			ignore_pricing_rule=1,
			is_pos=1,
			payments=[{"mode_of_payment": "Cash", "account": acc("Cash"), "amount": 90}],
			write_off_amount=10,
			write_off_account=WRITE_OFF,
			write_off_cost_center=acc("Main"),
		)
		events = [
			e
			for e in get_settlement_events(US_COMPANY, "2026-12-31")
			if e["voucher_no"] == invoice.name and e["against_voucher_no"] == invoice.name
		]
		self.assertEqual(
			sorted((flt(e["amount_in_account_currency"], 2), flt(e["amount"], 2)) for e in events),
			[(10, 11), (90, 99)],
		)
		self.assert_invariants("2026-03-31")
