# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.payment_ledger_entry.payment_ledger_entry import (
	get_amount_against_voucher,
)
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.stock.doctype.item.test_item import create_item


class TestPaymentLedgerEntry(FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_item()
		self.create_customer()
		self.create_supplier()

	def tearDown(self):
		frappe.db.rollback()

	def create_company(self):
		company = None
		if frappe.db.exists("Company", "_Test Payment Ledger"):
			company = frappe.get_doc("Company", "_Test Payment Ledger")
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": "_Test Payment Ledger",
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
					"stock_received_but_not_billed": "Stock Received But Not Billed - _PL",
					"expenses_included_in_valuation": "Expenses Included In Valuation - _PL",
				}
			)
			company = company.save()

		self.company = company.name
		self.cost_center = company.cost_center
		self.warehouse = "All Warehouses - _PL"
		self.income_account = "Sales - _PL"
		self.expense_account = "Cost of Goods Sold - _PL"
		self.debit_to = "Debtors - _PL"
		self.creditors = "Creditors - _PL"

		# create bank account
		if frappe.db.exists("Account", "HDFC - _PL"):
			self.bank = "HDFC - _PL"
		else:
			bank_acc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "HDFC",
					"parent_account": "Bank Accounts - _PL",
					"company": self.company,
				}
			)
			bank_acc.save()
			self.bank = bank_acc.name

	def create_item(self):
		item = create_item(
			item_code="_Test PLE Item", is_stock_item=0, company=self.company, warehouse=self.warehouse
		)
		self.item = item if isinstance(item, str) else item.item_code

	def create_customer(self):
		if frappe.db.exists("Customer", "_Test PLE Customer"):
			self.customer = "_Test PLE Customer"
		else:
			customer = frappe.new_doc("Customer")
			customer.customer_name = "_Test PLE Customer"
			customer.type = "Individual"
			customer.save()
			self.customer = customer.name

	def create_supplier(self):
		if frappe.db.exists("Supplier", "_Test PLE Supplier"):
			self.supplier = "_Test PLE Supplier"
		else:
			supplier = frappe.new_doc("Supplier")
			supplier.supplier_name = "_Test PLE Supplier"
			supplier.supplier_group = "All Supplier Groups"
			supplier.type = "Company"
			supplier.save()
			self.supplier = supplier.name

	def create_sales_invoice(
		self, qty=1, rate=100, posting_date=nowdate(), do_not_save=False, do_not_submit=False
	):
		"""
		Helper function to populate default values in sales invoice
		"""
		sinv = create_sales_invoice(
			qty=qty,
			rate=rate,
			company=self.company,
			customer=self.customer,
			item_code=self.item,
			item_name=self.item,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			update_stock=0,
			currency="INR",
			is_pos=0,
			is_return=0,
			return_against=None,
			income_account=self.income_account,
			expense_account=self.expense_account,
			do_not_save=do_not_save,
			do_not_submit=do_not_submit,
		)
		return sinv

	def create_payment_entry(self, amount=100, posting_date=nowdate()):
		"""
		Helper function to populate default values in payment entry
		"""
		payment = create_payment_entry(
			company=self.company,
			payment_type="Receive",
			party_type="Customer",
			party=self.customer,
			paid_from=self.debit_to,
			paid_to=self.bank,
			paid_amount=amount,
		)
		payment.posting_date = posting_date
		return payment

	def create_purchase_invoice(self, qty=1, rate=100, posting_date=nowdate()):
		"""
		Helper function to fill default values in purchase invoice
		"""
		purchase_invoice = make_purchase_invoice(
			posting_date=posting_date,
			company=self.company,
			supplier=self.supplier,
			currency="INR",
			conversion_rate=1,
			warehouse=self.warehouse,
			cost_center=self.cost_center,
			item_code=self.item,
			qty=qty,
			rate=rate,
			expense_account=self.expense_account,
			do_not_save=True,
			do_not_submit=True,
		)
		purchase_invoice = purchase_invoice.save().submit()
		return purchase_invoice

	def test_payment_against_sales_invoice(self):
		amount = 200
		si = self.create_sales_invoice(qty=1, rate=amount)
		pe = get_payment_entry(si.doctype, si.name).insert().submit()
		ple_entries = frappe.db.get_list(
			"Payment Ledger Entry",
			filters={
				"voucher_type": pe.doctype,
				"voucher_no": pe.name,
				"against_voucher_type": si.doctype,
				"against_voucher_no": si.name,
				"is_cancelled": 0,
			},
			fields=["voucher_no", "against_voucher_no", "amount"],
		)

		expected_ple_entry = {"voucher_no": pe.name, "against_voucher_no": si.name, "amount": amount}
		self.assertEqual(expected_ple_entry, ple_entries[0])
		si.reload()
		self.assertEqual(si.get("outstanding_amount"), 0)

	def test_payment_against_purchase_invoice(self):
		amount = 1001
		pi = self.create_purchase_invoice(qty=1, rate=amount)
		pe = get_payment_entry(pi.doctype, pi.name).insert().submit()
		ple_entries = frappe.db.get_list(
			"Payment Ledger Entry",
			filters={
				"voucher_type": pe.doctype,
				"voucher_no": pe.name,
				"against_voucher_type": pi.doctype,
				"against_voucher_no": pi.name,
				"is_cancelled": 0,
			},
			fields=["voucher_no", "against_voucher_no", "amount"],
		)

		expected_ple_entry = {"voucher_no": pe.name, "against_voucher_no": pi.name, "amount": amount}
		self.assertEqual(expected_ple_entry, ple_entries[0])

		pi.reload()
		self.assertEqual(pi.get("outstanding_amount"), 0)

	# TODO: test debit note against invoice
	def test_credit_note_against_invoice(self):
		amount = 550
		si = self.create_sales_invoice(qty=1, rate=amount)
		get_payment_entry(si.doctype, si.name).insert().submit()
		si.reload()

		self.assertEqual(si.get("outstanding_amount"), 0)

		# make return invoice and asset -ve outstanding
		si_ret = make_return_doc("Sales Invoice", si.name)
		si_ret = si_ret.save().submit()
		si.reload()
		self.assertEqual(si.get("outstanding_amount"), -(amount))

		paid_amount = get_amount_against_voucher(si.doctype, si.name)
		self.assertEqual(paid_amount, (amount * 2))

		# payment for return invoice
		get_payment_entry(si.doctype, si.name).insert().submit()
		si.reload()
		self.assertEqual(si.get("outstanding_amount"), 0)

		paid_amount = get_amount_against_voucher(si.doctype, si.name)
		self.assertEqual(paid_amount, amount)

	def test_debit_note_against_invoice(self):
		amount = 300
		pi = self.create_purchase_invoice(qty=1, rate=amount)
		get_payment_entry(pi.doctype, pi.name).insert().submit()
		pi.reload()

		self.assertEqual(pi.get("outstanding_amount"), 0)

		# make return invoice and asset -ve outstanding
		pi_ret = make_return_doc("Purchase Invoice", pi.name)
		pi_ret = pi_ret.save().submit()
		pi.reload()
		self.assertEqual(pi.get("outstanding_amount"), -(amount))

		paid_amount = get_amount_against_voucher(pi.doctype, pi.name)
		self.assertEqual(paid_amount, (amount * 2))

		# payment for return invoice
		get_payment_entry(pi.doctype, pi.name).insert().submit()
		pi.reload()
		self.assertEqual(pi.get("outstanding_amount"), 0)

		paid_amount = get_amount_against_voucher(pi.doctype, pi.name)
		self.assertEqual(paid_amount, amount)
