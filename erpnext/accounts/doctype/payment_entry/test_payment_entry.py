# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import flt, nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import (
	InvalidPaymentEntry,
	get_payment_entry,
)
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
	make_purchase_invoice,
	make_purchase_invoice_against_cost_center,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
	create_sales_invoice,
	create_sales_invoice_against_cost_center,
)
from erpnext.hr.doctype.expense_claim.test_expense_claim import make_expense_claim
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

test_dependencies = ["Item"]


class TestPaymentEntry(unittest.TestCase):
	def test_payment_entry_against_order(self):
		so = make_sales_order()
		pe = get_payment_entry("Sales Order", so.name, bank_account="_Test Cash - _TC")
		pe.paid_from = "Debtors - _TC"
		pe.insert()
		pe.submit()

		expected_gle = dict(
			(d[0], d) for d in [["Debtors - _TC", 0, 1000, so.name], ["_Test Cash - _TC", 1000.0, 0, None]]
		)

		self.validate_gl_entries(pe.name, expected_gle)

		so_advance_paid = frappe.db.get_value("Sales Order", so.name, "advance_paid")
		self.assertEqual(so_advance_paid, 1000)

		pe.cancel()

		so_advance_paid = frappe.db.get_value("Sales Order", so.name, "advance_paid")
		self.assertEqual(so_advance_paid, 0)

	def test_payment_entry_for_blocked_supplier_invoice(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.hold_type = "Invoices"
		supplier.save()

		self.assertRaises(frappe.ValidationError, make_purchase_invoice)

		supplier.on_hold = 0
		supplier.save()

	def test_payment_entry_for_blocked_supplier_payments(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.hold_type = "Payments"
		supplier.save()

		pi = make_purchase_invoice()

		self.assertRaises(
			frappe.ValidationError,
			get_payment_entry,
			dt="Purchase Invoice",
			dn=pi.name,
			bank_account="_Test Bank - _TC",
		)

		supplier.on_hold = 0
		supplier.save()

	def test_payment_entry_for_blocked_supplier_payments_today_date(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.hold_type = "Payments"
		supplier.release_date = nowdate()
		supplier.save()

		pi = make_purchase_invoice()

		self.assertRaises(
			frappe.ValidationError,
			get_payment_entry,
			dt="Purchase Invoice",
			dn=pi.name,
			bank_account="_Test Bank - _TC",
		)

		supplier.on_hold = 0
		supplier.save()

	def test_payment_entry_for_blocked_supplier_payments_past_date(self):
		# this test is meant to fail only if something fails in the try block
		with self.assertRaises(Exception):
			try:
				supplier = frappe.get_doc("Supplier", "_Test Supplier")
				supplier.on_hold = 1
				supplier.hold_type = "Payments"
				supplier.release_date = "2018-03-01"
				supplier.save()

				pi = make_purchase_invoice()

				get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")

				supplier.on_hold = 0
				supplier.save()
			except:
				pass
			else:
				raise Exception

	def test_payment_entry_against_si_usd_to_usd(self):
		si = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank USD - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.source_exchange_rate = 50
		pe.insert()
		pe.submit()

		expected_gle = dict(
			(d[0], d)
			for d in [
				["_Test Receivable USD - _TC", 0, 5000, si.name],
				["_Test Bank USD - _TC", 5000.0, 0, None],
			]
		)

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 0)

		pe.cancel()

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 100)

	def test_payment_entry_against_pi(self):
		pi = make_purchase_invoice(
			supplier="_Test Supplier USD",
			debit_to="_Test Payable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)
		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank USD - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.source_exchange_rate = 50
		pe.insert()
		pe.submit()

		expected_gle = dict(
			(d[0], d)
			for d in [
				["_Test Payable USD - _TC", 12500, 0, pi.name],
				["_Test Bank USD - _TC", 0, 12500, None],
			]
		)

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", pi.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 0)

	def test_payment_against_sales_invoice_to_check_status(self):
		si = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank USD - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.source_exchange_rate = 50
		pe.insert()
		pe.submit()

		outstanding_amount, status = frappe.db.get_value(
			"Sales Invoice", si.name, ["outstanding_amount", "status"]
		)
		self.assertEqual(flt(outstanding_amount), 0)
		self.assertEqual(status, "Paid")

		pe.cancel()

		outstanding_amount, status = frappe.db.get_value(
			"Sales Invoice", si.name, ["outstanding_amount", "status"]
		)
		self.assertEqual(flt(outstanding_amount), 100)
		self.assertEqual(status, "Unpaid")

	def test_payment_entry_against_payment_terms(self):
		si = create_sales_invoice(do_not_save=1, qty=1, rate=200)
		create_payment_terms_template()
		si.payment_terms_template = "Test Receivable Template"

		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 18,
			},
		)
		si.save()

		si.submit()

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Cash - _TC")
		pe.submit()
		si.load_from_db()

		self.assertEqual(pe.references[0].payment_term, "Basic Amount Receivable")
		self.assertEqual(pe.references[1].payment_term, "Tax Receivable")
		self.assertEqual(si.payment_schedule[0].paid_amount, 200.0)
		self.assertEqual(si.payment_schedule[1].paid_amount, 36.0)

	def test_payment_entry_against_payment_terms_with_discount(self):
		si = create_sales_invoice(do_not_save=1, qty=1, rate=200)
		create_payment_terms_template_with_discount()
		si.payment_terms_template = "Test Discount Template"

		frappe.db.set_value("Company", si.company, "default_discount_account", "Write Off - _TC")

		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 18,
			},
		)
		si.save()

		si.submit()

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Cash - _TC")
		pe.submit()
		si.load_from_db()

		self.assertEqual(pe.references[0].payment_term, "30 Credit Days with 10% Discount")
		self.assertEqual(si.payment_schedule[0].payment_amount, 236.0)
		self.assertEqual(si.payment_schedule[0].paid_amount, 212.40)
		self.assertEqual(si.payment_schedule[0].outstanding, 0)
		self.assertEqual(si.payment_schedule[0].discounted_amount, 23.6)

	def test_payment_against_purchase_invoice_to_check_status(self):
		pi = make_purchase_invoice(
			supplier="_Test Supplier USD",
			debit_to="_Test Payable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank USD - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.source_exchange_rate = 50
		pe.insert()
		pe.submit()

		outstanding_amount, status = frappe.db.get_value(
			"Purchase Invoice", pi.name, ["outstanding_amount", "status"]
		)
		self.assertEqual(flt(outstanding_amount), 0)
		self.assertEqual(status, "Paid")

		pe.cancel()

		outstanding_amount, status = frappe.db.get_value(
			"Purchase Invoice", pi.name, ["outstanding_amount", "status"]
		)
		self.assertEqual(flt(outstanding_amount), 250)
		self.assertEqual(status, "Unpaid")

	def test_payment_entry_against_ec(self):

		payable = frappe.get_cached_value("Company", "_Test Company", "default_payable_account")
		ec = make_expense_claim(payable, 300, 300, "_Test Company", "Travel Expenses - _TC")
		pe = get_payment_entry(
			"Expense Claim", ec.name, bank_account="_Test Bank USD - _TC", bank_amount=300
		)
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.source_exchange_rate = 1
		pe.paid_to = payable
		pe.insert()
		pe.submit()

		expected_gle = dict(
			(d[0], d) for d in [[payable, 300, 0, ec.name], ["_Test Bank USD - _TC", 0, 300, None]]
		)

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(
			frappe.db.get_value("Expense Claim", ec.name, "total_sanctioned_amount")
		) - flt(frappe.db.get_value("Expense Claim", ec.name, "total_amount_reimbursed"))
		self.assertEqual(outstanding_amount, 0)

	def test_payment_entry_against_si_usd_to_inr(self):
		si = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)
		pe = get_payment_entry(
			"Sales Invoice", si.name, party_amount=20, bank_account="_Test Bank - _TC", bank_amount=900
		)
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"

		self.assertEqual(pe.difference_amount, 100)

		pe.append(
			"deductions",
			{
				"account": "_Test Exchange Gain/Loss - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"amount": 100,
			},
		)
		pe.insert()
		pe.submit()

		expected_gle = dict(
			(d[0], d)
			for d in [
				["_Test Receivable USD - _TC", 0, 1000, si.name],
				["_Test Bank - _TC", 900, 0, None],
				["_Test Exchange Gain/Loss - _TC", 100.0, 0, None],
			]
		)

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 80)

	def test_payment_entry_against_si_usd_to_usd_with_deduction_in_base_currency(self):
		si = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
			do_not_save=1,
		)

		si.plc_conversion_rate = 50
		si.save()
		si.submit()

		pe = get_payment_entry(
			"Sales Invoice", si.name, party_amount=20, bank_account="_Test Bank USD - _TC", bank_amount=900
		)

		pe.source_exchange_rate = 45.263
		pe.target_exchange_rate = 45.263
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"

		pe.append(
			"deductions",
			{
				"account": "_Test Exchange Gain/Loss - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"amount": 94.80,
			},
		)

		pe.save()

		self.assertEqual(flt(pe.difference_amount, 2), 0.0)
		self.assertEqual(flt(pe.unallocated_amount, 2), 0.0)

	def test_payment_entry_retrieves_last_exchange_rate(self):
		from erpnext.setup.doctype.currency_exchange.test_currency_exchange import (
			save_new_records,
			test_records,
		)

		save_new_records(test_records)

		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = "Pay"
		pe.company = "_Test Company"
		pe.posting_date = "2016-01-10"
		pe.paid_from = "_Test Bank USD - _TC"
		pe.paid_to = "_Test Bank - _TC"
		pe.paid_amount = 100
		pe.received_amount = 100
		pe.reference_no = "3"
		pe.reference_date = "2016-01-10"
		pe.party_type = "Supplier"
		pe.party = "_Test Supplier USD"

		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.set_exchange_rate()
		pe.set_amounts()

		self.assertEqual(
			pe.source_exchange_rate, 65.1, "{0} is not equal to {1}".format(pe.source_exchange_rate, 65.1)
		)

	def test_internal_transfer_usd_to_inr(self):
		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = "Internal Transfer"
		pe.company = "_Test Company"
		pe.paid_from = "_Test Bank USD - _TC"
		pe.paid_to = "_Test Bank - _TC"
		pe.paid_amount = 100
		pe.source_exchange_rate = 50
		pe.received_amount = 4500
		pe.reference_no = "2"
		pe.reference_date = nowdate()

		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.set_exchange_rate()
		pe.set_amounts()

		self.assertEqual(pe.difference_amount, 500)

		pe.append(
			"deductions",
			{
				"account": "_Test Exchange Gain/Loss - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"amount": 500,
			},
		)

		pe.insert()
		pe.submit()

		expected_gle = dict(
			(d[0], d)
			for d in [
				["_Test Bank USD - _TC", 0, 5000, None],
				["_Test Bank - _TC", 4500, 0, None],
				["_Test Exchange Gain/Loss - _TC", 500.0, 0, None],
			]
		)

		self.validate_gl_entries(pe.name, expected_gle)

	def test_payment_against_negative_sales_invoice(self):
		pe1 = frappe.new_doc("Payment Entry")
		pe1.payment_type = "Pay"
		pe1.company = "_Test Company"
		pe1.party_type = "Customer"
		pe1.party = "_Test Customer"
		pe1.paid_from = "_Test Cash - _TC"
		pe1.paid_amount = 100
		pe1.received_amount = 100

		self.assertRaises(InvalidPaymentEntry, pe1.validate)

		si1 = create_sales_invoice()

		# create full payment entry against si1
		pe2 = get_payment_entry("Sales Invoice", si1.name, bank_account="_Test Cash - _TC")
		pe2.insert()
		pe2.submit()

		# create return entry against si1
		create_sales_invoice(is_return=1, return_against=si1.name, qty=-1)
		si1_outstanding = frappe.db.get_value("Sales Invoice", si1.name, "outstanding_amount")
		self.assertEqual(si1_outstanding, -100)

		# pay more than outstanding against si1
		pe3 = get_payment_entry("Sales Invoice", si1.name, bank_account="_Test Cash - _TC")
		pe3.paid_amount = pe3.received_amount = 300
		self.assertRaises(InvalidPaymentEntry, pe3.validate)

		# pay negative outstanding against si1
		pe3.paid_to = "Debtors - _TC"
		pe3.paid_amount = pe3.received_amount = 100

		pe3.insert()
		pe3.submit()

		expected_gle = dict(
			(d[0], d) for d in [["Debtors - _TC", 100, 0, si1.name], ["_Test Cash - _TC", 0, 100, None]]
		)

		self.validate_gl_entries(pe3.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si1.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 0)

		pe3.cancel()

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si1.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, -100)

	def validate_gl_entries(self, voucher_no, expected_gle):
		gl_entries = self.get_gle(voucher_no)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_gle[gle.account][0], gle.account)
			self.assertEqual(expected_gle[gle.account][1], gle.debit)
			self.assertEqual(expected_gle[gle.account][2], gle.credit)
			self.assertEqual(expected_gle[gle.account][3], gle.against_voucher)

	def get_gle(self, voucher_no):
		return frappe.db.sql(
			"""select account, debit, credit, against_voucher
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""",
			voucher_no,
			as_dict=1,
		)

	def test_payment_entry_write_off_difference(self):
		si = create_sales_invoice()
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Cash - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.received_amount = pe.paid_amount = 110
		pe.insert()

		self.assertEqual(pe.unallocated_amount, 10)

		pe.received_amount = pe.paid_amount = 95
		pe.append(
			"deductions",
			{"account": "_Test Write Off - _TC", "cost_center": "_Test Cost Center - _TC", "amount": 5},
		)
		pe.save()

		self.assertEqual(pe.unallocated_amount, 0)
		self.assertEqual(pe.difference_amount, 0)

		pe.submit()

		expected_gle = dict(
			(d[0], d)
			for d in [
				["Debtors - _TC", 0, 100, si.name],
				["_Test Cash - _TC", 95, 0, None],
				["_Test Write Off - _TC", 5, 0, None],
			]
		)

		self.validate_gl_entries(pe.name, expected_gle)

	def test_payment_entry_exchange_gain_loss(self):
		si = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank USD - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.source_exchange_rate = 55

		pe.append(
			"deductions",
			{
				"account": "_Test Exchange Gain/Loss - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"amount": -500,
			},
		)
		pe.save()

		self.assertEqual(pe.unallocated_amount, 0)
		self.assertEqual(pe.difference_amount, 0)

		pe.submit()

		expected_gle = dict(
			(d[0], d)
			for d in [
				["_Test Receivable USD - _TC", 0, 5000, si.name],
				["_Test Bank USD - _TC", 5500, 0, None],
				["_Test Exchange Gain/Loss - _TC", 0, 500, None],
			]
		)

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 0)

	def test_payment_entry_against_sales_invoice_with_cost_centre(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")

		si = create_sales_invoice_against_cost_center(cost_center=cost_center, debit_to="Debtors - _TC")

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		self.assertEqual(pe.cost_center, si.cost_center)

		pe.reference_no = "112211-1"
		pe.reference_date = nowdate()
		pe.paid_to = "_Test Bank - _TC"
		pe.paid_amount = si.grand_total
		pe.insert()
		pe.submit()

		expected_values = {
			"_Test Bank - _TC": {"cost_center": cost_center},
			"Debtors - _TC": {"cost_center": cost_center},
		}

		gl_entries = frappe.db.sql(
			"""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""",
			pe.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_payment_entry_against_purchase_invoice_with_cost_center(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")

		pi = make_purchase_invoice_against_cost_center(
			cost_center=cost_center, credit_to="Creditors - _TC"
		)

		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
		self.assertEqual(pe.cost_center, pi.cost_center)

		pe.reference_no = "112222-1"
		pe.reference_date = nowdate()
		pe.paid_from = "_Test Bank - _TC"
		pe.paid_amount = pi.grand_total
		pe.insert()
		pe.submit()

		expected_values = {
			"_Test Bank - _TC": {"cost_center": cost_center},
			"Creditors - _TC": {"cost_center": cost_center},
		}

		gl_entries = frappe.db.sql(
			"""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""",
			pe.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_payment_entry_account_and_party_balance_with_cost_center(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.utils import get_balance_on

		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")

		si = create_sales_invoice_against_cost_center(cost_center=cost_center, debit_to="Debtors - _TC")

		account_balance = get_balance_on(account="_Test Bank - _TC", cost_center=si.cost_center)
		party_balance = get_balance_on(
			party_type="Customer", party=si.customer, cost_center=si.cost_center
		)
		party_account_balance = get_balance_on(si.debit_to, cost_center=si.cost_center)

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "112211-1"
		pe.reference_date = nowdate()
		pe.paid_to = "_Test Bank - _TC"
		pe.paid_amount = si.grand_total
		pe.insert()
		pe.submit()

		expected_account_balance = account_balance + si.grand_total
		expected_party_balance = party_balance - si.grand_total
		expected_party_account_balance = party_account_balance - si.grand_total

		account_balance = get_balance_on(account=pe.paid_to, cost_center=pe.cost_center)
		party_balance = get_balance_on(party_type="Customer", party=pe.party, cost_center=pe.cost_center)
		party_account_balance = get_balance_on(account=pe.paid_from, cost_center=pe.cost_center)

		self.assertEqual(pe.cost_center, si.cost_center)
		self.assertEqual(flt(expected_account_balance), account_balance)
		self.assertEqual(flt(expected_party_balance), party_balance)
		self.assertEqual(flt(expected_party_account_balance), party_account_balance)

	def test_multi_currency_payment_entry_with_taxes(self):
		payment_entry = create_payment_entry(
			party="_Test Supplier USD", paid_to="_Test Payable USD - _TC", save=True
		)
		payment_entry.append(
			"taxes",
			{
				"account_head": "_Test Account Service Tax - _TC",
				"charge_type": "Actual",
				"tax_amount": 10,
				"add_deduct_tax": "Add",
				"description": "Test",
			},
		)

		payment_entry.save()
		self.assertEqual(payment_entry.base_total_taxes_and_charges, 10)
		self.assertEqual(
			flt(payment_entry.total_taxes_and_charges, 2), flt(10 / payment_entry.target_exchange_rate, 2)
		)


def create_payment_entry(**args):
	payment_entry = frappe.new_doc("Payment Entry")
	payment_entry.company = args.get("company") or "_Test Company"
	payment_entry.payment_type = args.get("payment_type") or "Pay"
	payment_entry.party_type = args.get("party_type") or "Supplier"
	payment_entry.party = args.get("party") or "_Test Supplier"
	payment_entry.paid_from = args.get("paid_from") or "_Test Bank - _TC"
	payment_entry.paid_to = args.get("paid_to") or "Creditors - _TC"
	payment_entry.paid_amount = args.get("paid_amount") or 1000

	payment_entry.setup_party_account_field()
	payment_entry.set_missing_values()
	payment_entry.set_exchange_rate()
	payment_entry.received_amount = payment_entry.paid_amount / payment_entry.target_exchange_rate
	payment_entry.reference_no = "Test001"
	payment_entry.reference_date = nowdate()

	if args.get("save"):
		payment_entry.save()
		if args.get("submit"):
			payment_entry.submit()

	return payment_entry


def create_payment_terms_template():

	create_payment_term("Basic Amount Receivable")
	create_payment_term("Tax Receivable")

	if not frappe.db.exists("Payment Terms Template", "Test Receivable Template"):
		payment_term_template = frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "Test Receivable Template",
				"allocate_payment_based_on_payment_terms": 1,
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"payment_term": "Basic Amount Receivable",
						"invoice_portion": 84.746,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 1,
					},
					{
						"doctype": "Payment Terms Template Detail",
						"payment_term": "Tax Receivable",
						"invoice_portion": 15.254,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 2,
					},
				],
			}
		).insert()


def create_payment_terms_template_with_discount():

	create_payment_term("30 Credit Days with 10% Discount")

	if not frappe.db.exists("Payment Terms Template", "Test Discount Template"):
		payment_term_template = frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "Test Discount Template",
				"allocate_payment_based_on_payment_terms": 1,
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"payment_term": "30 Credit Days with 10% Discount",
						"invoice_portion": 100,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 2,
						"discount": 10,
						"discount_validity_based_on": "Day(s) after invoice date",
						"discount_validity": 1,
					}
				],
			}
		).insert()


def create_payment_term(name):
	if not frappe.db.exists("Payment Term", name):
		frappe.get_doc({"doctype": "Payment Term", "payment_term_name": name}).insert()
