# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_months, getdate

from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.tests.utils import if_lending_app_installed, if_lending_app_not_installed


class TestBankClearance(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_warehouse(
			warehouse_name="_Test Warehouse",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		create_item("_Test Item")
		create_cost_center(cost_center_name="_Test Cost Center", company="_Test Company")

		clear_payment_entries()
		clear_loan_transactions()
		clear_pos_sales_invoices()
		make_bank_account()
		add_transactions()

	# Basic test case to test if bank clearance tool doesn't break
	# Detailed test can be added later
	@if_lending_app_not_installed
	def test_bank_clearance(self):
		bank_clearance = frappe.get_doc("Bank Clearance")
		bank_clearance.account = "_Test Bank Clearance - _TC"
		bank_clearance.from_date = add_months(getdate(), -1)
		bank_clearance.to_date = getdate()
		bank_clearance.get_payment_entries()
		self.assertEqual(len(bank_clearance.payment_entries), 1)

	@if_lending_app_installed
	def test_bank_clearance_with_loan(self):
		from lending.loan_management.doctype.loan.test_loan import (
			create_loan,
			create_loan_accounts,
			create_loan_product,
			create_repayment_entry,
			make_loan_disbursement_entry,
		)

		def create_loan_masters():
			create_loan_product(
				"Clearance Loan",
				"Clearance Loan",
				2000000,
				13.5,
				25,
				0,
				5,
				"Cash",
				"_Test Bank Clearance - _TC",
				"_Test Bank Clearance - _TC",
				"Loan Account - _TC",
				"Interest Income Account - _TC",
				"Penalty Income Account - _TC",
			)

		def make_loan():
			loan = create_loan(
				"_Test Customer",
				"Clearance Loan",
				280000,
				"Repay Over Number of Periods",
				20,
				applicant_type="Customer",
			)
			loan.submit()
			make_loan_disbursement_entry(loan.name, loan.loan_amount, disbursement_date=getdate())
			repayment_entry = create_repayment_entry(loan.name, "_Test Customer", getdate(), loan.loan_amount)
			repayment_entry.save()
			repayment_entry.submit()

		create_loan_accounts()
		create_loan_masters()
		make_loan()

		bank_clearance = frappe.get_doc("Bank Clearance")
		bank_clearance.account = "_Test Bank Clearance - _TC"
		bank_clearance.from_date = add_months(getdate(), -1)
		bank_clearance.to_date = getdate()
		bank_clearance.get_payment_entries()
		self.assertEqual(len(bank_clearance.payment_entries), 3)

	def test_update_clearance_date_on_si(self):
		sales_invoice = make_pos_sales_invoice()

		date = getdate()
		bank_clearance = frappe.get_doc("Bank Clearance")
		bank_clearance.account = "_Test Bank Clearance - _TC"
		bank_clearance.from_date = add_months(date, -1)
		bank_clearance.to_date = date
		bank_clearance.include_pos_transactions = 1
		bank_clearance.get_payment_entries()

		self.assertNotEqual(len(bank_clearance.payment_entries), 0)
		for payment in bank_clearance.payment_entries:
			if payment.payment_entry == sales_invoice.name:
				payment.clearance_date = date

		bank_clearance.update_clearance_date()

		si_clearance_date = frappe.db.get_value(
			"Sales Invoice Payment",
			{"parent": sales_invoice.name, "account": bank_clearance.account},
			"clearance_date",
		)

		self.assertEqual(si_clearance_date, date)


def clear_payment_entries():
	frappe.db.delete("Payment Entry")


def clear_pos_sales_invoices():
	frappe.db.delete("Sales Invoice", {"is_pos": 1})


@if_lending_app_installed
def clear_loan_transactions():
	for dt in [
		"Loan Disbursement",
		"Loan Repayment",
	]:
		frappe.db.delete(dt)


def make_bank_account():
	if not frappe.db.get_value("Account", "_Test Bank Clearance - _TC"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_type": "Bank",
				"account_name": "_Test Bank Clearance",
				"company": "_Test Company",
				"parent_account": "Bank Accounts - _TC",
			}
		).insert()


def add_transactions():
	make_payment_entry()


def make_payment_entry():
	from erpnext.buying.doctype.supplier.test_supplier import create_supplier

	supplier = create_supplier(supplier_name="_Test Supplier")
	pi = make_purchase_invoice(
		supplier=supplier,
		supplier_warehouse="_Test Warehouse - _TC",
		expense_account="Cost of Goods Sold - _TC",
		uom="Nos",
		qty=1,
		rate=690,
	)
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank Clearance - _TC")
	pe.reference_no = "Conrad Oct 18"
	pe.reference_date = "2018-10-24"
	pe.insert()
	pe.submit()


def make_pos_sales_invoice():
	from erpnext.accounts.doctype.opening_invoice_creation_tool.test_opening_invoice_creation_tool import (
		make_customer,
	)

	mode_of_payment = frappe.get_doc({"doctype": "Mode of Payment", "name": "Cash"})

	if not frappe.db.get_value("Mode of Payment Account", {"company": "_Test Company", "parent": "Cash"}):
		mode_of_payment.append(
			"accounts", {"company": "_Test Company", "default_account": "_Test Bank Clearance - _TC"}
		)
		mode_of_payment.save()

	customer = make_customer(customer="_Test Customer")

	si = create_sales_invoice(customer=customer, item="_Test Item", is_pos=1, qty=1, rate=1000, do_not_save=1)
	si.set("payments", [])
	si.append(
		"payments", {"mode_of_payment": "Cash", "account": "_Test Bank Clearance - _TC", "amount": 1000}
	)
	si.insert()
	si.submit()

	return si
