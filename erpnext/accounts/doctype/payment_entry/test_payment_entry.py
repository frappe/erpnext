# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, flt, nowdate

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_outstanding_reference_documents,
	get_party_details,
	get_payment_entry,
	get_reference_details,
)
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
	make_purchase_invoice,
	make_purchase_invoice_against_cost_center,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
	create_sales_invoice,
	create_sales_invoice_against_cost_center,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.setup.doctype.employee.test_employee import make_employee

test_dependencies = ["Item"]


class TestPaymentEntry(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def get_journals_for(self, voucher_type: str, voucher_no: str) -> list:
		journals = []
		if voucher_type and voucher_no:
			journals = frappe.db.get_all(
				"Journal Entry Account",
				filters={"reference_type": voucher_type, "reference_name": voucher_no, "docstatus": 1},
				fields=["parent"],
			)
		return journals

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

	def test_payment_against_sales_order_usd_to_inr(self):
		so = make_sales_order(
			customer="_Test Customer USD", currency="USD", qty=1, rate=100, do_not_submit=True
		)
		so.conversion_rate = 50
		so.submit()
		pe = get_payment_entry("Sales Order", so.name)
		pe.source_exchange_rate = 55
		pe.received_amount = 5500
		pe.insert()
		pe.submit()

		# there should be no difference amount
		pe.reload()
		self.assertEqual(pe.difference_amount, 0)
		self.assertEqual(pe.deductions, [])

		expected_gle = dict(
			(d[0], d)
			for d in [["_Test Receivable USD - _TC", 0, 5500, so.name], [pe.paid_to, 5500.0, 0, None]]
		)

		self.validate_gl_entries(pe.name, expected_gle)

		so_advance_paid = frappe.db.get_value("Sales Order", so.name, "advance_paid")
		self.assertEqual(so_advance_paid, 100)

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
			except Exception:
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

		frappe.db.set_single_value("Accounts Settings", "book_tax_discount_loss", 1)
		pe_with_tax_loss = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Cash - _TC")

		self.assertEqual(pe_with_tax_loss.references[0].payment_term, "30 Credit Days with 10% Discount")
		self.assertEqual(pe_with_tax_loss.references[0].allocated_amount, 236.0)
		self.assertEqual(pe_with_tax_loss.paid_amount, 212.4)
		self.assertEqual(pe_with_tax_loss.deductions[0].amount, 20.0)  # Loss on Income
		self.assertEqual(pe_with_tax_loss.deductions[1].amount, 3.6)  # Loss on Tax
		self.assertEqual(pe_with_tax_loss.deductions[1].account, "_Test Account Service Tax - _TC")

		frappe.db.set_single_value("Accounts Settings", "book_tax_discount_loss", 0)
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Cash - _TC")

		self.assertEqual(pe.references[0].allocated_amount, 236.0)
		self.assertEqual(pe.paid_amount, 212.4)
		self.assertEqual(pe.deductions[0].amount, 23.6)

		pe.submit()
		si.load_from_db()

		self.assertEqual(pe.references[0].payment_term, "30 Credit Days with 10% Discount")
		self.assertEqual(si.payment_schedule[0].payment_amount, 236.0)
		self.assertEqual(si.payment_schedule[0].paid_amount, 212.40)
		self.assertEqual(si.payment_schedule[0].outstanding, 0)
		self.assertEqual(si.payment_schedule[0].discounted_amount, 23.6)

	def test_payment_entry_against_payment_terms_with_discount_amount(self):
		si = create_sales_invoice(do_not_save=1, qty=1, rate=200)

		si.payment_terms_template = "Test Discount Amount Template"
		create_payment_terms_template_with_discount(
			name="30 Credit Days with Rs.50 Discount",
			discount_type="Amount",
			discount=50,
			template_name="Test Discount Amount Template",
		)
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

		# Set reference date past discount cut off date
		pe_1 = get_payment_entry(
			"Sales Invoice",
			si.name,
			bank_account="_Test Cash - _TC",
			reference_date=frappe.utils.add_days(si.posting_date, 2),
		)
		self.assertEqual(pe_1.paid_amount, 236.0)  # discount not applied

		# Test if tax loss is booked on enabling configuration
		frappe.db.set_single_value("Accounts Settings", "book_tax_discount_loss", 1)
		pe_with_tax_loss = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Cash - _TC")
		self.assertEqual(pe_with_tax_loss.deductions[0].amount, 42.37)  # Loss on Income
		self.assertEqual(pe_with_tax_loss.deductions[1].amount, 7.63)  # Loss on Tax
		self.assertEqual(pe_with_tax_loss.deductions[1].account, "_Test Account Service Tax - _TC")

		frappe.db.set_single_value("Accounts Settings", "book_tax_discount_loss", 0)
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Cash - _TC")
		self.assertEqual(pe.references[0].allocated_amount, 236.0)
		self.assertEqual(pe.paid_amount, 186)
		self.assertEqual(pe.deductions[0].amount, 50.0)

		pe.submit()
		si.load_from_db()

		self.assertEqual(si.payment_schedule[0].payment_amount, 236.0)
		self.assertEqual(si.payment_schedule[0].paid_amount, 186)
		self.assertEqual(si.payment_schedule[0].outstanding, 0)
		self.assertEqual(si.payment_schedule[0].discounted_amount, 50)

	@change_settings(
		"Accounts Settings",
		{
			"allow_multi_currency_invoices_against_single_party_account": 1,
			"book_tax_discount_loss": 1,
		},
	)
	def test_payment_entry_multicurrency_si_with_base_currency_accounting_early_payment_discount(
		self,
	):
		"""
		1. Multi-currency SI with single currency accounting (company currency)
		2. PE with early payment discount
		3. Test if Paid Amount is calculated in company currency
		4. Test if deductions are calculated in company currency

		SI is in USD to document agreed amounts that are in USD, but the accounting is in base currency.
		"""
		si = create_sales_invoice(
			customer="_Test Customer",
			currency="USD",
			conversion_rate=50,
			do_not_save=1,
		)
		create_payment_terms_template_with_discount()
		si.payment_terms_template = "Test Discount Template"

		frappe.db.set_value("Company", si.company, "default_discount_account", "Write Off - _TC")
		si.save()
		si.submit()

		pe = get_payment_entry(
			"Sales Invoice",
			si.name,
			bank_account="_Test Bank - _TC",
		)
		pe.reference_no = si.name
		pe.reference_date = nowdate()

		# Early payment discount loss on income
		self.assertEqual(pe.paid_amount, 4500.0)  # Amount in company currency
		self.assertEqual(pe.received_amount, 4500.0)
		self.assertEqual(pe.deductions[0].amount, 500.0)
		self.assertEqual(pe.deductions[0].account, "Write Off - _TC")
		self.assertEqual(pe.difference_amount, 0.0)

		pe.insert()
		pe.submit()

		expected_gle = dict(
			(d[0], d)
			for d in [
				["Debtors - _TC", 0, 5000, si.name],
				["_Test Bank - _TC", 4500, 0, None],
				["Write Off - _TC", 500.0, 0, None],
			]
		)

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 0)

	def test_payment_entry_multicurrency_accounting_si_with_early_payment_discount(self):
		"""
		1. Multi-currency SI with multi-currency accounting
		2. PE with early payment discount and also exchange loss
		3. Test if Paid Amount is calculated in transaction currency
		4. Test if deductions are calculated in base/company currency
		5. Test if exchange loss is reflected in difference
		"""
		si = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
			do_not_save=1,
		)
		create_payment_terms_template_with_discount()
		si.payment_terms_template = "Test Discount Template"

		frappe.db.set_value("Company", si.company, "default_discount_account", "Write Off - _TC")
		si.save()
		si.submit()

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC", bank_amount=4700)
		pe.reference_no = si.name
		pe.reference_date = nowdate()

		# Early payment discount loss on income
		self.assertEqual(pe.paid_amount, 90.0)
		self.assertEqual(pe.received_amount, 4200.0)  # 5000 - 500 (discount) - 300 (exchange loss)
		self.assertEqual(pe.deductions[0].amount, 500.0)
		self.assertEqual(pe.deductions[0].account, "Write Off - _TC")

		# Exchange loss
		self.assertEqual(pe.difference_amount, 300.0)

		pe.append(
			"deductions",
			{
				"account": "_Test Exchange Gain/Loss - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"amount": 300.0,
			},
		)

		pe.insert()
		pe.submit()

		self.assertEqual(pe.difference_amount, 0.0)

		expected_gle = dict(
			(d[0], d)
			for d in [
				["_Test Receivable USD - _TC", 0, 5000, si.name],
				["_Test Bank - _TC", 4200, 0, None],
				["Write Off - _TC", 500.0, 0, None],
				["_Test Exchange Gain/Loss - _TC", 300.0, 0, None],
			]
		)

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 0)

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
		pe.save()

		self.assertEqual(flt(pe.difference_amount, 2), 0.0)
		self.assertEqual(flt(pe.unallocated_amount, 2), 0.0)

		# the exchange gain/loss amount is captured in reference table and a separate Journal will be submitted for them
		# payment entry will not be generating difference amount
		self.assertEqual(flt(pe.references[0].exchange_gain_loss, 2), -94.74)

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

		self.assertEqual(pe.source_exchange_rate, 65.1, f"{pe.source_exchange_rate} is not equal to {65.1}")

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
		si1 = create_sales_invoice()

		# create full payment entry against si1
		pe2 = get_payment_entry("Sales Invoice", si1.name, bank_account="_Test Cash - _TC")
		pe2.insert()
		pe2.submit()

		# create return entry against si1
		cr_note = create_sales_invoice(is_return=1, return_against=si1.name, qty=-1)
		si1_outstanding = frappe.db.get_value("Sales Invoice", si1.name, "outstanding_amount")

		# create JE(credit note) manually against si1 and cr_note
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": si1.company,
				"voucher_type": "Credit Note",
				"posting_date": nowdate(),
			}
		)
		je.append(
			"accounts",
			{
				"account": si1.debit_to,
				"party_type": "Customer",
				"party": si1.customer,
				"debit": 0,
				"credit": 100,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": 100,
				"reference_type": si1.doctype,
				"reference_name": si1.name,
				"cost_center": si1.items[0].cost_center,
			},
		)
		je.append(
			"accounts",
			{
				"account": cr_note.debit_to,
				"party_type": "Customer",
				"party": cr_note.customer,
				"debit": 100,
				"credit": 0,
				"debit_in_account_currency": 100,
				"credit_in_account_currency": 0,
				"reference_type": cr_note.doctype,
				"reference_name": cr_note.name,
				"cost_center": cr_note.items[0].cost_center,
			},
		)
		je.save().submit()

		si1_outstanding = frappe.db.get_value("Sales Invoice", si1.name, "outstanding_amount")
		self.assertEqual(si1_outstanding, -100)

		# pay more than outstanding against si1
		pe3 = get_payment_entry("Sales Invoice", si1.name, bank_account="_Test Cash - _TC")

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
		pe.save()

		self.assertEqual(pe.unallocated_amount, 0)
		self.assertEqual(pe.difference_amount, 0)
		self.assertEqual(pe.references[0].exchange_gain_loss, 500)
		pe.submit()

		expected_gle = dict(
			(d[0], d)
			for d in [
				["_Test Receivable USD - _TC", 0, 5500, si.name],
				["_Test Bank USD - _TC", 5500, 0, None],
			]
		)

		self.validate_gl_entries(pe.name, expected_gle)

		# Exchange gain/loss should have been posted through a journal
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)

		self.assertEqual(exc_je_for_si, exc_je_for_pe)
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

		pi = make_purchase_invoice_against_cost_center(cost_center=cost_center, credit_to="Creditors - _TC")

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
		party_balance = get_balance_on(party_type="Customer", party=si.customer, cost_center=si.cost_center)
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
		self.assertEqual(flt(expected_party_account_balance, 2), flt(party_account_balance, 2))

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

	def test_gl_of_multi_currency_payment_with_taxes(self):
		payment_entry = create_payment_entry(
			party="_Test Supplier USD", paid_to="_Test Payable USD - _TC", save=True
		)
		payment_entry.append(
			"taxes",
			{
				"account_head": "_Test Account Service Tax - _TC",
				"charge_type": "Actual",
				"tax_amount": 100,
				"add_deduct_tax": "Add",
				"description": "Test",
			},
		)
		payment_entry.target_exchange_rate = 80
		payment_entry.received_amount = 12.5
		payment_entry = payment_entry.submit()
		gle = qb.DocType("GL Entry")
		gl_entries = (
			qb.from_(gle)
			.select(
				gle.account,
				gle.debit,
				gle.credit,
				gle.debit_in_account_currency,
				gle.credit_in_account_currency,
			)
			.orderby(gle.account)
			.where(gle.voucher_no == payment_entry.name)
			.run()
		)

		expected_gl_entries = (
			("_Test Account Service Tax - _TC", 100.0, 0.0, 100.0, 0.0),
			("_Test Bank - _TC", 0.0, 1100.0, 0.0, 1100.0),
			("_Test Payable USD - _TC", 1000.0, 0.0, 12.5, 0),
		)

		self.assertEqual(gl_entries, expected_gl_entries)

	def test_payment_entry_against_onhold_purchase_invoice(self):
		pi = make_purchase_invoice()

		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank USD - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"

		# block invoice after creating payment entry
		# since `get_payment_entry` will not attach blocked invoice to payment
		pi.block_invoice()
		with self.assertRaises(frappe.ValidationError) as err:
			pe.save()

		self.assertTrue("is on hold" in str(err.exception).lower())

	def test_payment_entry_for_employee(self):
		employee = make_employee("test_payment_entry@salary.com", company="_Test Company")
		create_payment_entry(party_type="Employee", party=employee, save=True)

	def test_duplicate_payment_entry_allocate_amount(self):
		si = create_sales_invoice()

		pe_draft = get_payment_entry("Sales Invoice", si.name)
		pe_draft.insert()

		pe = get_payment_entry("Sales Invoice", si.name)
		pe.submit()

		self.assertRaises(frappe.ValidationError, pe_draft.submit)

	def test_duplicate_payment_entry_partial_allocate_amount(self):
		si = create_sales_invoice()

		pe_draft = get_payment_entry("Sales Invoice", si.name)
		pe_draft.insert()

		pe = get_payment_entry("Sales Invoice", si.name)
		pe.received_amount = si.total / 2
		pe.references[0].allocated_amount = si.total / 2
		pe.submit()

		self.assertRaises(frappe.ValidationError, pe_draft.submit)

	def test_details_update_on_reference_table(self):
		from erpnext.accounts.party import get_party_account

		so = make_sales_order(
			customer="_Test Customer USD", currency="USD", qty=1, rate=100, do_not_submit=True
		)
		so.conversion_rate = 50
		so.submit()
		pe = get_payment_entry("Sales Order", so.name)
		pe.references.clear()
		pe.paid_from = "Debtors - _TC"
		pe.paid_from_account_currency = "INR"
		pe.source_exchange_rate = 50
		pe.save()

		ref_details = get_reference_details(
			so.doctype, so.name, pe.paid_from_account_currency, "Customer", so.customer
		)
		expected_response = {
			"account": get_party_account("Customer", so.customer, so.company),
			"account_type": None,  # only applies for Reverse Payment Entry
			"payment_type": None,  # only applies for Reverse Payment Entry
			"total_amount": 5000.0,
			"outstanding_amount": 5000.0,
			"exchange_rate": 1.0,
			"due_date": None,
			"bill_no": None,
		}
		self.assertDictEqual(ref_details, expected_response)

	@change_settings(
		"Accounts Settings",
		{
			"unlink_payment_on_cancellation_of_invoice": 1,
			"delete_linked_ledger_entries": 1,
			"allow_multi_currency_invoices_against_single_party_account": 1,
		},
	)
	def test_overallocation_validation_on_payment_terms(self):
		"""
		Validate Allocation on Payment Entry based on Payment Schedule. Upon overallocation, validation error must be thrown.

		"""
		customer = create_customer()
		create_payment_terms_template()

		# Validate allocation on base/company currency
		si1 = create_sales_invoice(do_not_save=1, qty=1, rate=200)
		si1.payment_terms_template = "Test Receivable Template"
		si1.save().submit()

		si1.reload()
		pe = get_payment_entry(si1.doctype, si1.name).save()
		# Allocated amount should be according to the payment schedule
		for idx, schedule in enumerate(si1.payment_schedule):
			with self.subTest(idx=idx):
				self.assertEqual(flt(schedule.payment_amount), flt(pe.references[idx].allocated_amount))
		pe.save()

		# Overallocation validation should trigger
		pe.paid_amount = 400
		pe.references[0].allocated_amount = 200
		pe.references[1].allocated_amount = 200
		self.assertRaises(frappe.ValidationError, pe.save)
		pe.delete()
		si1.cancel()
		si1.delete()

		# Validate allocation on foreign currency
		si2 = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=80,
			do_not_save=1,
		)
		si2.payment_terms_template = "Test Receivable Template"
		si2.save().submit()

		si2.reload()
		pe = get_payment_entry(si2.doctype, si2.name).save()
		# Allocated amount should be according to the payment schedule
		for idx, schedule in enumerate(si2.payment_schedule):
			with self.subTest(idx=idx):
				self.assertEqual(flt(schedule.payment_amount), flt(pe.references[idx].allocated_amount))
		pe.save()

		# Overallocation validation should trigger
		pe.paid_amount = 200
		pe.references[0].allocated_amount = 100
		pe.references[1].allocated_amount = 100
		self.assertRaises(frappe.ValidationError, pe.save)
		pe.delete()
		si2.cancel()
		si2.delete()

		# Validate allocation in base/company currency on a foreign currency document
		# when invoice is made is foreign currency, but posted to base/company currency debtors account
		si3 = create_sales_invoice(
			customer=customer,
			currency="USD",
			conversion_rate=80,
			do_not_save=1,
		)
		si3.payment_terms_template = "Test Receivable Template"
		si3.save().submit()

		si3.reload()
		pe = get_payment_entry(si3.doctype, si3.name).save()
		# Allocated amount should be equal to payment term outstanding
		self.assertEqual(len(pe.references), 2)
		for idx, ref in enumerate(pe.references):
			with self.subTest(idx=idx):
				self.assertEqual(ref.payment_term_outstanding, ref.allocated_amount)
		pe.save()

		# Overallocation validation should trigger
		pe.paid_amount = 16000
		pe.references[0].allocated_amount = 8000
		pe.references[1].allocated_amount = 8000
		self.assertRaises(frappe.ValidationError, pe.save)
		pe.delete()
		si3.cancel()
		si3.delete()

	@change_settings(
		"Accounts Settings",
		{
			"unlink_payment_on_cancellation_of_invoice": 1,
			"delete_linked_ledger_entries": 1,
			"allow_multi_currency_invoices_against_single_party_account": 1,
		},
	)
	def test_overallocation_validation_shouldnt_misfire(self):
		"""
		Overallocation validation shouldn't fire for Template without "Allocate Payment based on Payment Terms" enabled

		"""
		create_customer()
		create_payment_terms_template()

		template = frappe.get_doc("Payment Terms Template", "Test Receivable Template")
		template.allocate_payment_based_on_payment_terms = 0
		template.save()

		# Validate allocation on base/company currency
		si = create_sales_invoice(do_not_save=1, qty=1, rate=200)
		si.payment_terms_template = "Test Receivable Template"
		si.save().submit()

		si.reload()
		pe = get_payment_entry(si.doctype, si.name).save()
		# There will no term based allocation
		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.references[0].payment_term, None)
		self.assertEqual(flt(pe.references[0].allocated_amount), flt(si.grand_total))
		pe.save()

		# specify a term
		pe.references[0].payment_term = template.terms[0].payment_term
		# no validation error should be thrown
		pe.save()

		pe.paid_amount = si.grand_total + 1
		pe.references[0].allocated_amount = si.grand_total + 1
		self.assertRaises(frappe.ValidationError, pe.save)

		template = frappe.get_doc("Payment Terms Template", "Test Receivable Template")
		template.allocate_payment_based_on_payment_terms = 1
		template.save()

	def test_allocation_validation_for_sales_order(self):
		so = make_sales_order(do_not_save=True)
		so.items[0].rate = 99.55
		so.save().submit()
		self.assertGreater(so.rounded_total, 0.0)
		pe = get_payment_entry("Sales Order", so.name, bank_account="_Test Cash - _TC")
		pe.paid_from = "Debtors - _TC"
		pe.paid_amount = 45.55
		pe.references[0].allocated_amount = 45.55
		pe.save().submit()
		pe = get_payment_entry("Sales Order", so.name, bank_account="_Test Cash - _TC")
		pe.paid_from = "Debtors - _TC"
		# No validation error should be thrown here.
		pe.save().submit()

		so.reload()
		self.assertEqual(so.advance_paid, so.rounded_total)

	def test_receive_payment_from_payable_party_type(self):
		"""
		Checks GL entries generated while receiving payments from a Payable Party Type.
		"""
		pe = create_payment_entry(
			party_type="Supplier",
			party="_Test Supplier",
			payment_type="Receive",
			paid_from="Creditors - _TC",
			paid_to="_Test Cash - _TC",
			save=True,
			submit=True,
		)
		self.voucher_no = pe.name
		self.expected_gle = [
			{"account": "Creditors - _TC", "debit": 0.0, "credit": 1000.0},
			{"account": "_Test Cash - _TC", "debit": 1000.0, "credit": 0.0},
		]
		self.check_gl_entries()

	def test_payment_against_partial_return_invoice(self):
		"""
		Checks GL entries generated for partial return invoice payments.
		"""
		si = create_sales_invoice(qty=10, rate=10, customer="_Test Customer")
		credit_note = create_sales_invoice(
			qty=-4, rate=10, customer="_Test Customer", is_return=1, return_against=si.name
		)
		pe = create_payment_entry(
			party_type="Customer",
			party="_Test Customer",
			payment_type="Receive",
			paid_from="Debtors - _TC",
			paid_to="_Test Cash - _TC",
		)
		pe.set(
			"references",
			[
				{
					"reference_doctype": "Sales Invoice",
					"reference_name": si.name,
					"due_date": si.get("due_date"),
					"total_amount": si.grand_total,
					"outstanding_amount": si.outstanding_amount,
					"allocated_amount": si.outstanding_amount,
				},
				{
					"reference_doctype": "Sales Invoice",
					"reference_name": credit_note.name,
					"due_date": credit_note.get("due_date"),
					"total_amount": credit_note.grand_total,
					"outstanding_amount": credit_note.outstanding_amount,
					"allocated_amount": credit_note.outstanding_amount,
				},
			],
		)
		pe.save()
		pe.submit()
		self.assertEqual(pe.total_allocated_amount, 60)
		self.assertEqual(pe.unallocated_amount, 940)
		self.voucher_no = pe.name
		self.expected_gle = [
			{"account": "Debtors - _TC", "debit": 40.0, "credit": 0.0},
			{"account": "Debtors - _TC", "debit": 0.0, "credit": 940.0},
			{"account": "Debtors - _TC", "debit": 0.0, "credit": 100.0},
			{"account": "_Test Cash - _TC", "debit": 1000.0, "credit": 0.0},
		]
		self.check_gl_entries()

	def test_ledger_entries_for_advance_as_liability(self):
		company = "_Test Company"

		advance_account = create_account(
			parent_account="Current Assets - _TC",
			account_name="Advances Received",
			company=company,
			account_type="Receivable",
		)

		frappe.db.set_value(
			"Company",
			company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_received_account": advance_account,
			},
		)
		# Advance Payment
		pe = create_payment_entry(
			party_type="Customer",
			party="_Test Customer",
			payment_type="Receive",
			paid_from="Debtors - _TC",
			paid_to="_Test Cash - _TC",
		)
		pe.save()  # use save() to trigger set_liability_account()
		pe.submit()

		# Normal Invoice
		si = create_sales_invoice(qty=10, rate=100, customer="_Test Customer")

		pre_reconciliation_gle = [
			{"account": advance_account, "debit": 0.0, "credit": 1000.0},
			{"account": "_Test Cash - _TC", "debit": 1000.0, "credit": 0.0},
		]
		pre_reconciliation_ple = [
			{
				"account": advance_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": -1000.0,
			}
		]

		self.voucher_no = pe.name
		self.expected_gle = pre_reconciliation_gle
		self.expected_ple = pre_reconciliation_ple
		self.check_gl_entries()
		self.check_pl_entries()

		# Partially reconcile advance against invoice
		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = company
		pr.party_type = "Customer"
		pr.party = "_Test Customer"
		pr.receivable_payable_account = si.debit_to
		pr.default_advance_account = advance_account
		pr.payment_name = pe.name
		pr.invoice_name = si.name
		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)

		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.allocation[0].allocated_amount = 400
		pr.reconcile()

		# assert General and Payment Ledger entries post partial reconciliation
		self.expected_gle = [
			{"account": si.debit_to, "debit": 0.0, "credit": 400.0},
			{"account": advance_account, "debit": 400.0, "credit": 0.0},
			{"account": advance_account, "debit": 0.0, "credit": 1000.0},
			{"account": "_Test Cash - _TC", "debit": 1000.0, "credit": 0.0},
		]
		self.expected_ple = [
			{
				"account": advance_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": -1000.0,
			},
			{
				"account": si.debit_to,
				"voucher_no": pe.name,
				"against_voucher_no": si.name,
				"amount": -400.0,
			},
			{
				"account": advance_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": 400.0,
			},
		]
		self.check_gl_entries()
		self.check_pl_entries()

		# Unreconcile
		(
			frappe.get_doc(
				{
					"doctype": "Unreconcile Payment",
					"company": company,
					"voucher_type": pe.doctype,
					"voucher_no": pe.name,
					"allocations": [{"reference_doctype": si.doctype, "reference_name": si.name}],
				}
			)
			.save()
			.submit()
		)

		self.voucher_no = pe.name
		self.expected_gle = pre_reconciliation_gle
		self.expected_ple = pre_reconciliation_ple
		self.check_gl_entries()
		self.check_pl_entries()

	def test_advance_as_liability_against_order(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import (
			make_purchase_invoice as _make_purchase_invoice,
		)
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		company = "_Test Company"

		advance_account = create_account(
			parent_account="Current Liabilities - _TC",
			account_name="Advances Paid",
			company=company,
			account_type="Liability",
		)

		frappe.db.set_value(
			"Company",
			company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_paid_account": advance_account,
			},
		)

		po = create_purchase_order(supplier="_Test Supplier")
		pe = get_payment_entry("Purchase Order", po.name, bank_account="Cash - _TC")
		pe.save().submit()

		pre_reconciliation_gle = [
			{"account": "Cash - _TC", "debit": 0.0, "credit": 5000.0},
			{"account": advance_account, "debit": 5000.0, "credit": 0.0},
		]

		self.voucher_no = pe.name
		self.expected_gle = pre_reconciliation_gle
		self.check_gl_entries()

		# Make Purchase Invoice against the order
		pi = _make_purchase_invoice(po.name)
		pi.append(
			"advances",
			{
				"reference_type": pe.doctype,
				"reference_name": pe.name,
				"reference_row": pe.references[0].name,
				"advance_amount": 5000,
				"allocated_amount": 5000,
			},
		)
		pi.save().submit()

		# # assert General and Payment Ledger entries post partial reconciliation
		self.expected_gle = [
			{"account": pi.credit_to, "debit": 5000.0, "credit": 0.0},
			{"account": "Cash - _TC", "debit": 0.0, "credit": 5000.0},
			{"account": advance_account, "debit": 5000.0, "credit": 0.0},
			{"account": advance_account, "debit": 0.0, "credit": 5000.0},
		]

		self.voucher_no = pe.name
		self.check_gl_entries()

	def check_pl_entries(self):
		ple = frappe.qb.DocType("Payment Ledger Entry")
		pl_entries = (
			frappe.qb.from_(ple)
			.select(ple.account, ple.voucher_no, ple.against_voucher_no, ple.amount)
			.where((ple.voucher_no == self.voucher_no) & (ple.delinked == 0))
			.orderby(ple.creation)
		).run(as_dict=True)
		for row in range(len(self.expected_ple)):
			for field in ["account", "voucher_no", "against_voucher_no", "amount"]:
				self.assertEqual(self.expected_ple[row][field], pl_entries[row][field])

	def check_gl_entries(self):
		gle = frappe.qb.DocType("GL Entry")
		gl_entries = (
			frappe.qb.from_(gle)
			.select(
				gle.account,
				gle.debit,
				gle.credit,
			)
			.where((gle.voucher_no == self.voucher_no) & (gle.is_cancelled == 0))
			.orderby(gle.account, gle.debit, gle.credit, order=frappe.qb.desc)
		).run(as_dict=True)
		for row in range(len(self.expected_gle)):
			for field in ["account", "debit", "credit"]:
				self.assertEqual(self.expected_gle[row][field], gl_entries[row][field])

	def test_outstanding_invoices_api(self):
		"""
		Test if `get_outstanding_reference_documents` fetches invoices in the right order.
		"""
		customer = create_customer("Max Mustermann", "INR")
		create_payment_terms_template()

		# SI has an earlier due date and SI2 has a later due date
		si = create_sales_invoice(qty=1, rate=100, customer=customer, posting_date=add_days(nowdate(), -4))
		si2 = create_sales_invoice(do_not_save=1, qty=1, rate=100, customer=customer)
		si2.payment_terms_template = "Test Receivable Template"
		si2.submit()

		args = {
			"posting_date": nowdate(),
			"company": "_Test Company",
			"party_type": "Customer",
			"payment_type": "Pay",
			"party": customer,
			"party_account": "Debtors - _TC",
		}
		args.update(
			{
				"get_outstanding_invoices": True,
				"from_posting_date": add_days(nowdate(), -4),
				"to_posting_date": add_days(nowdate(), 2),
			}
		)
		references = get_outstanding_reference_documents(args)

		self.assertEqual(len(references), 3)
		self.assertEqual(references[0].voucher_no, si.name)
		self.assertEqual(references[1].voucher_no, si2.name)
		self.assertEqual(references[2].voucher_no, si2.name)
		self.assertEqual(references[1].payment_term, "Basic Amount Receivable")
		self.assertEqual(references[2].payment_term, "Tax Receivable")

	def test_reverse_payment_reconciliation(self):
		customer = create_customer(frappe.generate_hash(length=10), "INR")
		pe = create_payment_entry(
			party_type="Customer",
			party=customer,
			payment_type="Receive",
			paid_from="Debtors - _TC",
			paid_to="_Test Cash - _TC",
		)
		pe.submit()

		reverse_pe = create_payment_entry(
			party_type="Customer",
			party=customer,
			payment_type="Pay",
			paid_from="_Test Cash - _TC",
			paid_to="Debtors - _TC",
		)
		reverse_pe.submit()

		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = "_Test Company"
		pr.party_type = "Customer"
		pr.party = customer
		pr.receivable_payable_account = "Debtors - _TC"
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)

		self.assertEqual(reverse_pe.name, pr.invoices[0].invoice_number)
		self.assertEqual(pe.name, pr.payments[0].reference_name)

		invoices = [x.as_dict() for x in pr.invoices]
		payments = [pr.payments[0].as_dict()]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

	def test_advance_reverse_payment_reconciliation(self):
		company = "_Test Company"
		customer = create_customer(frappe.generate_hash(length=10), "INR")
		advance_account = create_account(
			parent_account="Current Liabilities - _TC",
			account_name="Advances Received",
			company=company,
			account_type="Receivable",
		)

		frappe.db.set_value(
			"Company",
			company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_received_account": advance_account,
			},
		)
		# Reverse Payment(essentially an Invoice)
		reverse_pe = create_payment_entry(
			party_type="Customer",
			party=customer,
			payment_type="Pay",
			paid_from="_Test Cash - _TC",
			paid_to=advance_account,
		)
		reverse_pe.save()  # use save() to trigger set_liability_account()
		reverse_pe.submit()

		# Advance Payment
		pe = create_payment_entry(
			party_type="Customer",
			party=customer,
			payment_type="Receive",
			paid_from=advance_account,
			paid_to="_Test Cash - _TC",
		)
		pe.save()  # use save() to trigger set_liability_account()
		pe.submit()

		# Partially reconcile advance against invoice
		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = company
		pr.party_type = "Customer"
		pr.party = customer
		pr.receivable_payable_account = "Debtors - _TC"
		pr.default_advance_account = advance_account
		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)

		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.allocation[0].allocated_amount = 400
		pr.reconcile()

		# assert General and Payment Ledger entries post partial reconciliation
		self.expected_gle = [
			{"account": advance_account, "debit": 400.0, "credit": 0.0},
			{"account": advance_account, "debit": 0.0, "credit": 1000.0},
			{"account": advance_account, "debit": 0.0, "credit": 400.0},
			{"account": "_Test Cash - _TC", "debit": 1000.0, "credit": 0.0},
		]
		self.expected_ple = [
			{
				"account": advance_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": -1000.0,
			},
			{
				"account": advance_account,
				"voucher_no": pe.name,
				"against_voucher_no": reverse_pe.name,
				"amount": -400.0,
			},
			{
				"account": advance_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": 400.0,
			},
		]
		self.voucher_no = pe.name
		self.check_gl_entries()
		self.check_pl_entries()

		# Unreconcile
		(
			frappe.get_doc(
				{
					"doctype": "Unreconcile Payment",
					"company": company,
					"voucher_type": pe.doctype,
					"voucher_no": pe.name,
					"allocations": [
						{"reference_doctype": reverse_pe.doctype, "reference_name": reverse_pe.name}
					],
				}
			)
			.save()
			.submit()
		)

		# assert General and Payment Ledger entries post unreconciliation
		self.expected_gle = [
			{"account": advance_account, "debit": 0.0, "credit": 1000.0},
			{"account": "_Test Cash - _TC", "debit": 1000.0, "credit": 0.0},
		]
		self.expected_ple = [
			{
				"account": advance_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": -1000.0,
			},
		]
		self.voucher_no = pe.name
		self.check_gl_entries()
		self.check_pl_entries()

	def test_opening_flag_for_advance_as_liability(self):
		company = "_Test Company"

		advance_account = create_account(
			parent_account="Current Assets - _TC",
			account_name="Advances Received",
			company=company,
			account_type="Receivable",
		)

		# Enable Advance in separate party account
		frappe.db.set_value(
			"Company",
			company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_received_account": advance_account,
			},
		)
		# Advance Payment
		adv = create_payment_entry(
			party_type="Customer",
			party="_Test Customer",
			payment_type="Receive",
			paid_from="Debtors - _TC",
			paid_to="_Test Cash - _TC",
		)
		adv.is_opening = "Yes"
		adv.save()  # use save() to trigger set_liability_account()
		adv.submit()

		gl_with_opening_set = frappe.db.get_all(
			"GL Entry", filters={"voucher_no": adv.name, "is_opening": "Yes"}
		)
		# 'Is Opening' can be 'Yes' for Advances in separate party account
		self.assertNotEqual(gl_with_opening_set, [])

		# Disable Advance in separate party account
		frappe.db.set_value(
			"Company",
			company,
			{
				"book_advance_payments_in_separate_party_account": 0,
				"default_advance_received_account": None,
			},
		)
		payment = create_payment_entry(
			party_type="Customer",
			party="_Test Customer",
			payment_type="Receive",
			paid_from="Debtors - _TC",
			paid_to="_Test Cash - _TC",
		)
		payment.is_opening = "Yes"
		payment.save()
		payment.submit()
		gl_with_opening_set = frappe.db.get_all(
			"GL Entry", filters={"voucher_no": payment.name, "is_opening": "Yes"}
		)
		# 'Is Opening' should always be 'No' for normal advance payments
		self.assertEqual(gl_with_opening_set, [])


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

	get_party_details(
		payment_entry.company, payment_entry.party_type, payment_entry.party, payment_entry.posting_date
	)

	if args.get("save"):
		payment_entry.save()
		if args.get("submit"):
			payment_entry.submit()

	return payment_entry


def create_payment_terms_template():
	create_payment_term("Basic Amount Receivable")
	create_payment_term("Tax Receivable")

	if not frappe.db.exists("Payment Terms Template", "Test Receivable Template"):
		frappe.get_doc(
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


def create_payment_terms_template_with_discount(
	name=None, discount_type=None, discount=None, template_name=None
):
	"""
	Create a Payment Terms Template with %  or amount discount.
	"""
	create_payment_term(name or "30 Credit Days with 10% Discount")
	template_name = template_name or "Test Discount Template"

	if not frappe.db.exists("Payment Terms Template", template_name):
		frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": template_name,
				"allocate_payment_based_on_payment_terms": 1,
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"payment_term": name or "30 Credit Days with 10% Discount",
						"invoice_portion": 100,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 2,
						"discount_type": discount_type or "Percentage",
						"discount": discount or 10,
						"discount_validity_based_on": "Day(s) after invoice date",
						"discount_validity": 1,
					}
				],
			}
		).insert()


def create_payment_term(name):
	if not frappe.db.exists("Payment Term", name):
		frappe.get_doc({"doctype": "Payment Term", "payment_term_name": name}).insert()


def create_customer(name="_Test Customer 2 USD", currency="USD"):
	customer = None
	if frappe.db.exists("Customer", name):
		customer = name
	else:
		customer = frappe.new_doc("Customer")
		customer.customer_name = name
		customer.default_currency = currency
		customer.type = "Individual"
		customer.save()
		customer = customer.name
	return customer
