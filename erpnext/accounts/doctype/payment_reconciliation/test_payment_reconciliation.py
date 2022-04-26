# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.party import get_party_account
from erpnext.stock.doctype.item.test_item import create_item


class TestPaymentReconciliation(FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_item()
		self.create_customer()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def create_company(self):
		company = None
		if frappe.db.exists("Company", "_Test Payment Reconciliation"):
			company = frappe.get_doc("Company", "_Test Payment Reconciliation")
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": "_Test Payment Reconciliation",
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			)
			company = company.save()

		self.company = company.name
		self.cost_center = company.cost_center
		self.warehouse = "All Warehouses - _PR"
		self.income_account = "Sales - _PR"
		self.expense_account = "Cost of Goods Sold - _PR"
		self.debit_to = "Debtors - _PR"
		self.creditors = "Creditors - _PR"

		# create bank account
		if frappe.db.exists("Account", "HDFC - _PR"):
			self.bank = "HDFC - _PR"
		else:
			bank_acc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "HDFC",
					"parent_account": "Bank Accounts - _PR",
					"company": self.company,
				}
			)
			bank_acc.save()
			self.bank = bank_acc.name

	def create_item(self):
		item = create_item(
			item_code="_Test PR Item", is_stock_item=0, company=self.company, warehouse=self.warehouse
		)
		self.item = item if isinstance(item, str) else item.item_code

	def create_customer(self):
		if frappe.db.exists("Customer", "_Test PR Customer"):
			self.customer = "_Test PR Customer"
		else:
			customer = frappe.new_doc("Customer")
			customer.customer_name = "_Test PR Customer"
			customer.type = "Individual"
			customer.save()
			self.customer = customer.name

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

	def clear_old_entries(self):
		invoices = frappe.db.get_list(
			"Sales Invoice", filters={"company": self.company, "docstatus": 1}, fields=["name"]
		)
		for inv in invoices:
			frappe.get_doc("Sales Invoice", inv.name).cancel()
			frappe.delete_doc("Sales Invoice", inv.name, force=True)

		payments = frappe.db.get_list(
			"Payment Entry", filters={"company": self.company, "docstatus": 1}, fields=["name"]
		)
		for pay in payments:
			frappe.get_doc("Payment Entry", pay.name).cancel()
			frappe.delete_doc("Payment Entry", pay.name, force=True)

		journals = frappe.db.get_list(
			"Journal Entry", filters={"company": self.company, "docstatus": 1}, fields=["name"]
		)
		for je in journals:
			frappe.get_doc("Journal Entry", je.name).cancel()
			frappe.delete_doc("Journal Entry", je.name, force=True)

	def create_payment_reconciliation(self):
		pr = frappe.new_doc("Payment Reconciliation")
		pr.company = self.company
		pr.party_type = "Customer"
		pr.party = self.customer
		pr.receivable_payable_account = get_party_account(pr.party_type, pr.party, pr.company)
		pr.from_invoice_date = nowdate()
		pr.to_invoice_date = nowdate()
		pr.from_payment_date = nowdate()
		pr.to_payment_date = nowdate()
		return pr

	def create_journal_entry(
		self, acc1=None, acc2=None, amount=0, posting_date=None, cost_center=None
	):
		je = frappe.new_doc("Journal Entry")
		je.posting_date = posting_date or nowdate()
		je.company = self.company
		je.user_remark = "test"
		if not cost_center:
			cost_center = self.cost_center
		je.set(
			"accounts",
			[
				{
					"account": acc1,
					"cost_center": cost_center,
					"debit_in_account_currency": amount if amount > 0 else 0,
					"credit_in_account_currency": abs(amount) if amount < 0 else 0,
				},
				{
					"account": acc2,
					"cost_center": cost_center,
					"credit_in_account_currency": amount if amount > 0 else 0,
					"debit_in_account_currency": abs(amount) if amount < 0 else 0,
				},
			],
		)
		return je

	def test_filter_min_max(self):
		# check filter condition minimum and maximum amount
		self.create_sales_invoice(qty=1, rate=350)
		self.create_sales_invoice(qty=1, rate=450)
		self.create_sales_invoice(qty=1, rate=550)
		self.create_payment_entry(amount=350).save().submit()
		self.create_payment_entry(amount=450).save().submit()
		self.create_payment_entry(amount=550).save().submit()

		pr = self.create_payment_reconciliation()
		pr.minimum_invoice_amount = 400
		pr.maximum_invoice_amount = 500
		pr.minimum_payment_amount = 300
		pr.maximum_payment_amount = 600
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.get("invoices")), 1)
		self.assertEqual(len(pr.get("payments")), 3)

		pr.minimum_invoice_amount = 300
		pr.maximum_invoice_amount = 600
		pr.minimum_payment_amount = 400
		pr.maximum_payment_amount = 500
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.get("invoices")), 3)
		self.assertEqual(len(pr.get("payments")), 1)

		pr.minimum_invoice_amount = (
			pr.maximum_invoice_amount
		) = pr.minimum_payment_amount = pr.maximum_payment_amount = 0
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.get("invoices")), 3)
		self.assertEqual(len(pr.get("payments")), 3)

	def test_filter_posting_date(self):
		# check filter condition using transaction date
		transaction_date = add_days(nowdate(), 0)
		amount = 999
		self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		self.create_payment_entry(amount=amount, posting_date=transaction_date).save().submit()

		pr = self.create_payment_reconciliation()
		pr.from_invoice_date = pr.to_invoice_date = transaction_date
		pr.from_payment_date = pr.to_payment_date = transaction_date

		pr.get_unreconciled_entries()

		# assert only si and pe are fetched
		self.assertEqual(len(pr.get("invoices")), 2)
		self.assertEqual(len(pr.get("payments")), 1)

	def test_filter_invoice_limit(self):
		# check filter condition - invoice limit
		transaction_date = nowdate()
		rate = 100
		invoices = []
		payments = []
		for i in range(5):
			invoices.append(self.create_sales_invoice(qty=1, rate=rate, posting_date=transaction_date))
			pe = self.create_payment_entry(amount=rate, posting_date=transaction_date).save().submit()
			payments.append(pe)

		pr = self.create_payment_reconciliation()
		pr.from_invoice_date = pr.to_invoice_date = transaction_date
		pr.from_payment_date = pr.to_payment_date = transaction_date
		pr.invoice_limit = pr.payment_limit = 2
		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.get("invoices")), 2)
		self.assertEqual(len(pr.get("payments")), 2)

	def test_payment_against_invoice(self):
		# check if payment ledger entry is made for SI against PE
		si = self.create_sales_invoice(qty=1, rate=200)
		pe = self.create_payment_entry(amount=200).save().submit()

		pr = self.create_payment_reconciliation()
		pr.minimum_invoice_amount = 200
		pr.maximum_invoice_amount = 200

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices") if x.invoice_number == si.name]
		payments = [
			x.as_dict()
			for x in pr.get("payments")
			if x.reference_name == pe.name and x.reference_type == "Payment Entry"
		]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		si.reload()
		self.assertEqual(si.status, "Paid")
		ple_entries = frappe.db.get_list(
			"Payment Ledger Entry",
			filters={
				"voucher_type": "Payment Entry",
				"voucher_no": pe.name,
				"against_voucher_type": "Sales Invoice",
				"against_voucher_no": si.name,
				"is_cancelled": 0,
			},
			fields=["voucher_no", "against_voucher_no", "amount"],
		)

		# check if payment ledger entry is created
		self.assertEqual(
			ple_entries[0],
			frappe._dict({"voucher_no": pe.name, "against_voucher_no": si.name, "amount": 200}),
		)

	def test_payment_against_journal(self):
		# check if payment ledger entry is made for SI against PE
		# | voucher_no    | against_voucher_no | amount |
		# |---------------+--------------------+--------|
		# | payment entry | journal entry      |    921 |

		transaction_date = nowdate()

		sales = "Sales - _PR"
		amount = 921
		# debit debtors account to simulate an invoice
		je = self.create_journal_entry(self.debit_to, sales, amount, transaction_date)
		je.accounts[0].party_type = "Customer"
		je.accounts[0].party = self.customer
		je.save()
		je.submit()

		pe = self.create_payment_entry(amount=amount, posting_date=transaction_date).save().submit()

		pr = self.create_payment_reconciliation()
		pr.minimum_invoice_amount = pr.maximum_invoice_amount = amount
		pr.from_invoice_date = pr.to_invoice_date = transaction_date
		pr.from_payment_date = pr.to_payment_date = transaction_date

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices") if x.invoice_number == je.name]
		payments = [
			x.as_dict()
			for x in pr.get("payments")
			if x.reference_name == pe.name and x.reference_type == "Payment Entry"
		]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		ple_entries = frappe.db.get_list(
			"Payment Ledger Entry",
			filters={
				"voucher_type": "Payment Entry",
				"voucher_no": pe.name,
				"against_voucher_type": "Journal Entry",
				"against_voucher_no": je.name,
				"is_cancelled": 0,
			},
			fields=["voucher_no", "against_voucher_no", "amount"],
		)

		# check if payment ledger entry is created
		self.assertEqual(
			ple_entries[0],
			frappe._dict({"voucher_no": pe.name, "against_voucher_no": je.name, "amount": 921}),
		)

	def test_journal_against_invoice(self):
		# check if payment ledger entry is made for SI against PE
		# | voucher_no    | against_voucher_no | amount |
		# |---------------+--------------------+--------|
		# | journal entry | invoice            |    931 |
		transaction_date = nowdate()
		amount = 931
		si = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)

		# credit debtors account to simulate a payment
		je = self.create_journal_entry(self.bank, self.debit_to, amount, transaction_date)
		je.accounts[1].party_type = "Customer"
		je.accounts[1].party = self.customer
		je.save()
		je.submit()

		pr = self.create_payment_reconciliation()
		pr.minimum_invoice_amount = pr.maximum_invoice_amount = amount
		pr.minimum_payment_amount = pr.maximum_payment_amount = amount
		pr.from_invoice_date = pr.to_invoice_date = transaction_date
		pr.from_payment_date = pr.to_payment_date = transaction_date

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices") if x.invoice_number == si.name]
		payments = [
			x.as_dict()
			for x in pr.get("payments")
			if x.reference_name == je.name and x.reference_type == "Journal Entry"
		]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		ple_entries = frappe.db.get_list(
			"Payment Ledger Entry",
			filters={
				"voucher_type": "Journal Entry",
				"voucher_no": je.name,
				"against_voucher_type": "Sales Invoice",
				"against_voucher_no": si.name,
				"is_cancelled": 0,
			},
			fields=["voucher_no", "against_voucher_no", "amount"],
		)

		# check if payment ledger entry is created
		self.assertEqual(
			ple_entries[0],
			frappe._dict({"voucher_no": je.name, "against_voucher_no": si.name, "amount": amount}),
		)

	def test_journal_against_journal(self):
		# check if payment ledger entry is made for SI against PE
		# | voucher_no    | against_voucher_no | amount |
		# |---------------+--------------------+--------|
		# | journal entry | journal entry      |    941 |

		transaction_date = nowdate()
		sales = "Sales - _PR"
		amount = 941

		# debit debtors account to simulate a invoice
		je1 = self.create_journal_entry(self.debit_to, sales, amount, transaction_date)
		je1.accounts[0].party_type = "Customer"
		je1.accounts[0].party = self.customer
		je1.save()
		je1.submit()

		# credit debtors account to simulate a payment
		je2 = self.create_journal_entry(self.bank, self.debit_to, amount, transaction_date)
		je2.accounts[1].party_type = "Customer"
		je2.accounts[1].party = self.customer
		je2.save()
		je2.submit()

		pr = self.create_payment_reconciliation()
		pr.minimum_invoice_amount = pr.maximum_invoice_amount = amount
		pr.minimum_payment_amount = pr.maximum_payment_amount = amount
		pr.from_invoice_date = pr.to_invoice_date = transaction_date
		pr.from_payment_date = pr.to_payment_date = transaction_date

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices") if x.invoice_number == je1.name]
		payments = [
			x.as_dict()
			for x in pr.get("payments")
			if x.reference_name == je2.name and x.reference_type == "Journal Entry"
		]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		ple_entries = frappe.db.get_list(
			"Payment Ledger Entry",
			filters={
				"voucher_type": "Journal Entry",
				"voucher_no": je2.name,
				"against_voucher_type": "Journal Entry",
				"against_voucher_no": je1.name,
				"is_cancelled": 0,
			},
			fields=["voucher_no", "against_voucher_no", "amount"],
		)

		# check if payment ledger entry is created
		self.assertEqual(
			ple_entries[0],
			frappe._dict({"voucher_no": je2.name, "against_voucher_no": je1.name, "amount": amount}),
		)

	def test_cr_note_against_invoice(self):
		# check if payment ledger entry is made for SI against PE
		# | voucher_no    | against_voucher_no | amount |
		# |---------------+--------------------+--------|
		# | credit note   | journal entry      |    951 |
		# | journal entry | invoice            |    951 |

		transaction_date = nowdate()
		amount = 951

		si = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)

		cr_note = self.create_sales_invoice(
			qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		cr_note.is_return = 1
		cr_note = cr_note.save().submit()

		pr = self.create_payment_reconciliation()
		pr.minimum_invoice_amount = pr.maximum_invoice_amount = amount
		pr.minimum_payment_amount = pr.maximum_payment_amount = amount
		pr.from_invoice_date = pr.to_invoice_date = transaction_date
		pr.from_payment_date = pr.to_payment_date = transaction_date

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices") if x.invoice_number == si.name]
		payments = [
			x.as_dict()
			for x in pr.get("payments")
			if x.reference_name == cr_note.name and x.reference_type == "Sales Invoice"
		]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		je = frappe.db.get_list(
			"Journal Entry", fields={"docstatus": 1, "reference_name": si.name}, as_list=True
		)[0][0]

		# check if payment ledger entry is created
		self.assertNotEqual(
			frappe.db.exists(
				"Payment Ledger Entry",
				{"voucher_no": cr_note.name, "against_voucher_no": je, "amount": amount, "is_cancelled": 0},
			),
			False,
		)
		self.assertNotEqual(
			frappe.db.exists(
				"Payment Ledger Entry",
				{"voucher_no": je, "against_voucher_no": si.name, "amount": amount, "is_cancelled": 0},
			),
			False,
		)
