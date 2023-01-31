# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, nowdate

from erpnext import get_default_cost_center
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.party import get_party_account
from erpnext.stock.doctype.item.test_item import create_item


class TestPaymentReconciliation(FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_item()
		self.create_customer()
		self.create_account()
		self.create_cost_center()
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
		self.customer = make_customer("_Test PR Customer")
		self.customer2 = make_customer("_Test PR Customer 2")
		self.customer3 = make_customer("_Test PR Customer 3", "EUR")
		self.customer4 = make_customer("_Test PR Customer 4", "EUR")
		self.customer5 = make_customer("_Test PR Customer 5", "EUR")

	def create_account(self):
		account_name = "Debtors EUR"
		if not frappe.db.get_value(
			"Account", filters={"account_name": account_name, "company": self.company}
		):
			acc = frappe.new_doc("Account")
			acc.account_name = account_name
			acc.parent_account = "Accounts Receivable - _PR"
			acc.company = self.company
			acc.account_currency = "EUR"
			acc.account_type = "Receivable"
			acc.insert()
		else:
			name = frappe.db.get_value(
				"Account",
				filters={"account_name": account_name, "company": self.company},
				fieldname="name",
				pluck=True,
			)
			acc = frappe.get_doc("Account", name)
		self.debtors_eur = acc.name

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

	def create_payment_entry(self, amount=100, posting_date=nowdate(), customer=None):
		"""
		Helper function to populate default values in payment entry
		"""
		payment = create_payment_entry(
			company=self.company,
			payment_type="Receive",
			party_type="Customer",
			party=customer or self.customer,
			paid_from=self.debit_to,
			paid_to=self.bank,
			paid_amount=amount,
		)
		payment.posting_date = posting_date
		return payment

	def clear_old_entries(self):
		doctype_list = [
			"GL Entry",
			"Payment Ledger Entry",
			"Sales Invoice",
			"Purchase Invoice",
			"Payment Entry",
			"Journal Entry",
		]
		for doctype in doctype_list:
			qb.from_(qb.DocType(doctype)).delete().where(qb.DocType(doctype).company == self.company).run()

	def create_payment_reconciliation(self):
		pr = frappe.new_doc("Payment Reconciliation")
		pr.company = self.company
		pr.party_type = "Customer"
		pr.party = self.customer
		pr.receivable_payable_account = get_party_account(pr.party_type, pr.party, pr.company)
		pr.from_invoice_date = pr.to_invoice_date = pr.from_payment_date = pr.to_payment_date = nowdate()
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

	def create_cost_center(self):
		# Setup cost center
		cc_name = "Sub"

		self.main_cc = frappe.get_doc("Cost Center", get_default_cost_center(self.company))

		cc_exists = frappe.db.get_list("Cost Center", filters={"cost_center_name": cc_name})
		if cc_exists:
			self.sub_cc = frappe.get_doc("Cost Center", cc_exists[0].name)
		else:
			sub_cc = frappe.new_doc("Cost Center")
			sub_cc.cost_center_name = "Sub"
			sub_cc.parent_cost_center = self.main_cc.parent_cost_center
			sub_cc.company = self.main_cc.company
			self.sub_cc = sub_cc.save()

	def test_filter_min_max(self):
		# check filter condition minimum and maximum amount
		self.create_sales_invoice(qty=1, rate=300)
		self.create_sales_invoice(qty=1, rate=400)
		self.create_sales_invoice(qty=1, rate=500)
		self.create_payment_entry(amount=300).save().submit()
		self.create_payment_entry(amount=400).save().submit()
		self.create_payment_entry(amount=500).save().submit()

		pr = self.create_payment_reconciliation()
		pr.minimum_invoice_amount = 400
		pr.maximum_invoice_amount = 500
		pr.minimum_payment_amount = 300
		pr.maximum_payment_amount = 600
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.get("invoices")), 2)
		self.assertEqual(len(pr.get("payments")), 3)

		pr.minimum_invoice_amount = 300
		pr.maximum_invoice_amount = 600
		pr.minimum_payment_amount = 400
		pr.maximum_payment_amount = 500
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.get("invoices")), 3)
		self.assertEqual(len(pr.get("payments")), 2)

		pr.minimum_invoice_amount = (
			pr.maximum_invoice_amount
		) = pr.minimum_payment_amount = pr.maximum_payment_amount = 0
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.get("invoices")), 3)
		self.assertEqual(len(pr.get("payments")), 3)

	def test_filter_posting_date(self):
		# check filter condition using transaction date
		date1 = nowdate()
		date2 = add_days(nowdate(), -1)
		amount = 100
		self.create_sales_invoice(qty=1, rate=amount, posting_date=date1)
		si2 = self.create_sales_invoice(
			qty=1, rate=amount, posting_date=date2, do_not_save=True, do_not_submit=True
		)
		si2.set_posting_time = 1
		si2.posting_date = date2
		si2.save().submit()
		self.create_payment_entry(amount=amount, posting_date=date1).save().submit()
		self.create_payment_entry(amount=amount, posting_date=date2).save().submit()

		pr = self.create_payment_reconciliation()
		pr.from_invoice_date = pr.to_invoice_date = date1
		pr.from_payment_date = pr.to_payment_date = date1

		pr.get_unreconciled_entries()
		# assert only si and pe are fetched
		self.assertEqual(len(pr.get("invoices")), 1)
		self.assertEqual(len(pr.get("payments")), 1)

		pr.from_invoice_date = date2
		pr.to_invoice_date = date1
		pr.from_payment_date = date2
		pr.to_payment_date = date1

		pr.get_unreconciled_entries()
		# assert only si and pe are fetched
		self.assertEqual(len(pr.get("invoices")), 2)
		self.assertEqual(len(pr.get("payments")), 2)

	def test_filter_posting_date_case2(self):
		"""
		Posting date should not affect outstanding amount calculation
		"""

		from_date = add_days(nowdate(), -30)
		to_date = nowdate()
		self.create_payment_entry(amount=25, posting_date=from_date).submit()
		self.create_sales_invoice(rate=25, qty=1, posting_date=to_date)

		pr = self.create_payment_reconciliation()
		pr.from_invoice_date = pr.from_payment_date = from_date
		pr.to_invoice_date = pr.to_payment_date = to_date
		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)

		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		pr.from_invoice_date = pr.from_payment_date = to_date
		pr.to_invoice_date = pr.to_payment_date = to_date

		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.invoices), 0)

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
		pr.invoice_limit = 2
		pr.payment_limit = 3
		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.get("invoices")), 2)
		self.assertEqual(len(pr.get("payments")), 3)

	def test_payment_against_invoice(self):
		si = self.create_sales_invoice(qty=1, rate=200)
		pe = self.create_payment_entry(amount=55).save().submit()
		# second payment entry
		self.create_payment_entry(amount=35).save().submit()

		pr = self.create_payment_reconciliation()

		# reconcile multiple payments against invoice
		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		si.reload()
		self.assertEqual(si.status, "Partly Paid")
		# check PR tool output post reconciliation
		self.assertEqual(len(pr.get("invoices")), 1)
		self.assertEqual(pr.get("invoices")[0].get("outstanding_amount"), 110)
		self.assertEqual(pr.get("payments"), [])

		# cancel one PE
		pe.reload()
		pe.cancel()
		pr.get_unreconciled_entries()
		# check PR tool output
		self.assertEqual(len(pr.get("invoices")), 1)
		self.assertEqual(len(pr.get("payments")), 0)
		self.assertEqual(pr.get("invoices")[0].get("outstanding_amount"), 165)

	def test_payment_against_journal(self):
		transaction_date = nowdate()

		sales = "Sales - _PR"
		amount = 921
		# debit debtors account to record an invoice
		je = self.create_journal_entry(self.debit_to, sales, amount, transaction_date)
		je.accounts[0].party_type = "Customer"
		je.accounts[0].party = self.customer
		je.save()
		je.submit()

		self.create_payment_entry(amount=amount, posting_date=transaction_date).save().submit()

		pr = self.create_payment_reconciliation()
		pr.minimum_invoice_amount = pr.maximum_invoice_amount = amount
		pr.from_invoice_date = pr.to_invoice_date = transaction_date
		pr.from_payment_date = pr.to_payment_date = transaction_date

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		# check PR tool output
		self.assertEqual(len(pr.get("invoices")), 0)
		self.assertEqual(len(pr.get("payments")), 0)

	def test_journal_against_invoice(self):
		transaction_date = nowdate()
		amount = 100
		si = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)

		# credit debtors account to record a payment
		je = self.create_journal_entry(self.bank, self.debit_to, amount, transaction_date)
		je.accounts[1].party_type = "Customer"
		je.accounts[1].party = self.customer
		je.save()
		je.submit()

		pr = self.create_payment_reconciliation()

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		# assert outstanding
		si.reload()
		self.assertEqual(si.status, "Paid")
		self.assertEqual(si.outstanding_amount, 0)

		# check PR tool output
		self.assertEqual(len(pr.get("invoices")), 0)
		self.assertEqual(len(pr.get("payments")), 0)

	def test_journal_against_journal(self):
		transaction_date = nowdate()
		sales = "Sales - _PR"
		amount = 100

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

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		self.assertEqual(pr.get("invoices"), [])
		self.assertEqual(pr.get("payments"), [])

	def test_cr_note_against_invoice(self):
		transaction_date = nowdate()
		amount = 100

		si = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)

		cr_note = self.create_sales_invoice(
			qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		cr_note.is_return = 1
		cr_note = cr_note.save().submit()

		pr = self.create_payment_reconciliation()

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		pr.get_unreconciled_entries()
		# check reconciliation tool output
		# reconciled invoice and credit note shouldn't show up in selection
		self.assertEqual(pr.get("invoices"), [])
		self.assertEqual(pr.get("payments"), [])

		# assert outstanding
		si.reload()
		self.assertEqual(si.status, "Paid")
		self.assertEqual(si.outstanding_amount, 0)

	def test_cr_note_partial_against_invoice(self):
		transaction_date = nowdate()
		amount = 100
		allocated_amount = 80

		si = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)

		cr_note = self.create_sales_invoice(
			qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		cr_note.is_return = 1
		cr_note = cr_note.save().submit()

		pr = self.create_payment_reconciliation()

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.allocation[0].allocated_amount = allocated_amount
		pr.reconcile()

		# assert outstanding
		si.reload()
		self.assertEqual(si.status, "Partly Paid")
		self.assertEqual(si.outstanding_amount, 20)

		pr.get_unreconciled_entries()
		# check reconciliation tool output
		self.assertEqual(len(pr.get("invoices")), 1)
		self.assertEqual(len(pr.get("payments")), 1)
		self.assertEqual(pr.get("invoices")[0].outstanding_amount, 20)
		self.assertEqual(pr.get("payments")[0].amount, 20)

	def test_pr_output_foreign_currency_and_amount(self):
		# test for currency and amount invoices and payments
		transaction_date = nowdate()
		# In EUR
		amount = 100
		exchange_rate = 80

		si = self.create_sales_invoice(
			qty=1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		si.customer = self.customer3
		si.currency = "EUR"
		si.conversion_rate = exchange_rate
		si.debit_to = self.debtors_eur
		si = si.save().submit()

		cr_note = self.create_sales_invoice(
			qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		cr_note.customer = self.customer3
		cr_note.is_return = 1
		cr_note.currency = "EUR"
		cr_note.conversion_rate = exchange_rate
		cr_note.debit_to = self.debtors_eur
		cr_note = cr_note.save().submit()

		pr = self.create_payment_reconciliation()
		pr.party = self.customer3
		pr.receivable_payable_account = self.debtors_eur
		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)

		self.assertEqual(pr.invoices[0].amount, amount)
		self.assertEqual(pr.invoices[0].currency, "EUR")
		self.assertEqual(pr.payments[0].amount, amount)
		self.assertEqual(pr.payments[0].currency, "EUR")

		cr_note.cancel()

		pay = self.create_payment_entry(
			amount=amount, posting_date=transaction_date, customer=self.customer3
		)
		pay.paid_from = self.debtors_eur
		pay.paid_from_account_currency = "EUR"
		pay.source_exchange_rate = exchange_rate
		pay.received_amount = exchange_rate * amount
		pay = pay.save().submit()

		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		self.assertEqual(pr.payments[0].amount, amount)
		self.assertEqual(pr.payments[0].currency, "EUR")

	def test_difference_amount_via_journal_entry(self):
		# Make Sale Invoice
		si = self.create_sales_invoice(
			qty=1, rate=100, posting_date=nowdate(), do_not_save=True, do_not_submit=True
		)
		si.customer = self.customer4
		si.currency = "EUR"
		si.conversion_rate = 85
		si.debit_to = self.debtors_eur
		si.save().submit()

		# Make payment using Journal Entry
		je1 = self.create_journal_entry("HDFC - _PR", self.debtors_eur, 100, nowdate())
		je1.multi_currency = 1
		je1.accounts[0].exchange_rate = 1
		je1.accounts[0].credit_in_account_currency = 0
		je1.accounts[0].credit = 0
		je1.accounts[0].debit_in_account_currency = 8000
		je1.accounts[0].debit = 8000
		je1.accounts[1].party_type = "Customer"
		je1.accounts[1].party = self.customer4
		je1.accounts[1].exchange_rate = 80
		je1.accounts[1].credit_in_account_currency = 100
		je1.accounts[1].credit = 8000
		je1.accounts[1].debit_in_account_currency = 0
		je1.accounts[1].debit = 0
		je1.save()
		je1.submit()

		je2 = self.create_journal_entry("HDFC - _PR", self.debtors_eur, 200, nowdate())
		je2.multi_currency = 1
		je2.accounts[0].exchange_rate = 1
		je2.accounts[0].credit_in_account_currency = 0
		je2.accounts[0].credit = 0
		je2.accounts[0].debit_in_account_currency = 16000
		je2.accounts[0].debit = 16000
		je2.accounts[1].party_type = "Customer"
		je2.accounts[1].party = self.customer4
		je2.accounts[1].exchange_rate = 80
		je2.accounts[1].credit_in_account_currency = 200
		je1.accounts[1].credit = 16000
		je1.accounts[1].debit_in_account_currency = 0
		je1.accounts[1].debit = 0
		je2.save()
		je2.submit()

		pr = self.create_payment_reconciliation()
		pr.party = self.customer4
		pr.receivable_payable_account = self.debtors_eur
		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 2)

		# Test exact payment allocation
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [pr.payments[0].as_dict()]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

		self.assertEqual(pr.allocation[0].allocated_amount, 100)
		self.assertEqual(pr.allocation[0].difference_amount, -500)

		# Test partial payment allocation (with excess payment entry)
		pr.set("allocation", [])
		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [pr.payments[1].as_dict()]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.allocation[0].difference_account = "Exchange Gain/Loss - _PR"

		self.assertEqual(pr.allocation[0].allocated_amount, 100)
		self.assertEqual(pr.allocation[0].difference_amount, -500)

		# Check if difference journal entry gets generated for difference amount after reconciliation
		pr.reconcile()
		total_debit_amount = frappe.db.get_all(
			"Journal Entry Account",
			{"account": self.debtors_eur, "docstatus": 1, "reference_name": si.name},
			"sum(debit) as amount",
			group_by="reference_name",
		)[0].amount

		self.assertEqual(flt(total_debit_amount, 2), -500)

	def test_difference_amount_via_payment_entry(self):
		# Make Sale Invoice
		si = self.create_sales_invoice(
			qty=1, rate=100, posting_date=nowdate(), do_not_save=True, do_not_submit=True
		)
		si.customer = self.customer5
		si.currency = "EUR"
		si.conversion_rate = 85
		si.debit_to = self.debtors_eur
		si.save().submit()

		# Make payment using Payment Entry
		pe1 = create_payment_entry(
			company=self.company,
			payment_type="Receive",
			party_type="Customer",
			party=self.customer5,
			paid_from=self.debtors_eur,
			paid_to=self.bank,
			paid_amount=100,
		)

		pe1.source_exchange_rate = 80
		pe1.received_amount = 8000
		pe1.save()
		pe1.submit()

		pe2 = create_payment_entry(
			company=self.company,
			payment_type="Receive",
			party_type="Customer",
			party=self.customer5,
			paid_from=self.debtors_eur,
			paid_to=self.bank,
			paid_amount=200,
		)

		pe2.source_exchange_rate = 80
		pe2.received_amount = 16000
		pe2.save()
		pe2.submit()

		pr = self.create_payment_reconciliation()
		pr.party = self.customer5
		pr.receivable_payable_account = self.debtors_eur
		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 2)

		invoices = [x.as_dict() for x in pr.invoices]
		payments = [pr.payments[0].as_dict()]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

		self.assertEqual(pr.allocation[0].allocated_amount, 100)
		self.assertEqual(pr.allocation[0].difference_amount, -500)

		pr.set("allocation", [])
		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [pr.payments[1].as_dict()]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

		self.assertEqual(pr.allocation[0].allocated_amount, 100)
		self.assertEqual(pr.allocation[0].difference_amount, -500)

	def test_differing_cost_center_on_invoice_and_payment(self):
		"""
		Cost Center filter should not affect outstanding amount calculation
		"""

		si = self.create_sales_invoice(qty=1, rate=100, do_not_submit=True)
		si.cost_center = self.main_cc.name
		si.submit()
		pr = get_payment_entry(si.doctype, si.name)
		pr.cost_center = self.sub_cc.name
		pr = pr.save().submit()

		pr = self.create_payment_reconciliation()
		pr.cost_center = self.main_cc.name

		pr.get_unreconciled_entries()

		# check PR tool output
		self.assertEqual(len(pr.get("invoices")), 0)
		self.assertEqual(len(pr.get("payments")), 0)

	def test_cost_center_filter_on_vouchers(self):
		"""
		Test Cost Center filter is applied on Invoices, Payment Entries and Journals
		"""
		transaction_date = nowdate()
		rate = 100

		# 'Main - PR' Cost Center
		si1 = self.create_sales_invoice(
			qty=1, rate=rate, posting_date=transaction_date, do_not_submit=True
		)
		si1.cost_center = self.main_cc.name
		si1.submit()

		pe1 = self.create_payment_entry(posting_date=transaction_date, amount=rate)
		pe1.cost_center = self.main_cc.name
		pe1 = pe1.save().submit()

		je1 = self.create_journal_entry(self.bank, self.debit_to, 100, transaction_date)
		je1.accounts[0].cost_center = self.main_cc.name
		je1.accounts[1].cost_center = self.main_cc.name
		je1.accounts[1].party_type = "Customer"
		je1.accounts[1].party = self.customer
		je1 = je1.save().submit()

		# 'Sub - PR' Cost Center
		si2 = self.create_sales_invoice(
			qty=1, rate=rate, posting_date=transaction_date, do_not_submit=True
		)
		si2.cost_center = self.sub_cc.name
		si2.submit()

		pe2 = self.create_payment_entry(posting_date=transaction_date, amount=rate)
		pe2.cost_center = self.sub_cc.name
		pe2 = pe2.save().submit()

		je2 = self.create_journal_entry(self.bank, self.debit_to, 100, transaction_date)
		je2.accounts[0].cost_center = self.sub_cc.name
		je2.accounts[1].cost_center = self.sub_cc.name
		je2.accounts[1].party_type = "Customer"
		je2.accounts[1].party = self.customer
		je2 = je2.save().submit()

		pr = self.create_payment_reconciliation()
		pr.cost_center = self.main_cc.name

		pr.get_unreconciled_entries()

		# check PR tool output
		self.assertEqual(len(pr.get("invoices")), 1)
		self.assertEqual(pr.get("invoices")[0].get("invoice_number"), si1.name)
		self.assertEqual(len(pr.get("payments")), 2)
		payment_vouchers = [x.get("reference_name") for x in pr.get("payments")]
		self.assertCountEqual(payment_vouchers, [pe1.name, je1.name])

		# Change cost center
		pr.cost_center = self.sub_cc.name

		pr.get_unreconciled_entries()

		# check PR tool output
		self.assertEqual(len(pr.get("invoices")), 1)
		self.assertEqual(pr.get("invoices")[0].get("invoice_number"), si2.name)
		self.assertEqual(len(pr.get("payments")), 2)
		payment_vouchers = [x.get("reference_name") for x in pr.get("payments")]
		self.assertCountEqual(payment_vouchers, [je2.name, pe2.name])


def make_customer(customer_name, currency=None):
	if not frappe.db.exists("Customer", customer_name):
		customer = frappe.new_doc("Customer")
		customer.customer_name = customer_name
		customer.type = "Individual"

		if currency:
			customer.default_currency = currency
		customer.save()
		return customer.name
	else:
		return customer_name
