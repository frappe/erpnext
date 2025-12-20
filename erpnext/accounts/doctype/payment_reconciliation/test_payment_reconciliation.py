# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe import qb
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_years, flt, getdate, nowdate, today
from frappe.utils.data import getdate as convert_to_date

from erpnext import get_default_cost_center
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.stock.doctype.item.test_item import create_item

EXTRA_TEST_RECORD_DEPENDENCIES = ["Item"]


class TestPaymentReconciliation(IntegrationTestCase):
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
		self.cash = "Cash - _PR"

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
		accounts = [
			{
				"attribute": "debtors_eur",
				"account_name": "Debtors EUR",
				"parent_account": "Accounts Receivable - _PR",
				"account_currency": "EUR",
				"account_type": "Receivable",
			},
			{
				"attribute": "creditors_usd",
				"account_name": "Payable USD",
				"parent_account": "Accounts Payable - _PR",
				"account_currency": "USD",
				"account_type": "Payable",
			},
			# 'Payable' account for capturing advance paid, under 'Assets' group
			{
				"attribute": "advance_payable_account",
				"account_name": "Advance Paid",
				"parent_account": "Current Assets - _PR",
				"account_currency": "INR",
				"account_type": "Payable",
			},
			# 'Receivable' account for capturing advance received, under 'Liabilities' group
			{
				"attribute": "advance_receivable_account",
				"account_name": "Advance Received",
				"parent_account": "Current Liabilities - _PR",
				"account_currency": "INR",
				"account_type": "Receivable",
			},
		]

		for x in accounts:
			x = frappe._dict(x)
			if not frappe.db.get_value(
				"Account", filters={"account_name": x.account_name, "company": self.company}
			):
				acc = frappe.new_doc("Account")
				acc.account_name = x.account_name
				acc.parent_account = x.parent_account
				acc.company = self.company
				acc.account_currency = x.account_currency
				acc.account_type = x.account_type
				acc.insert()
			else:
				name = frappe.db.get_value(
					"Account",
					filters={"account_name": x.account_name, "company": self.company},
					fieldname="name",
					pluck=True,
				)
				acc = frappe.get_doc("Account", name)
			setattr(self, x.attribute, acc.name)

	def create_sales_invoice(
		self, qty=1, rate=100, posting_date=None, do_not_save=False, do_not_submit=False
	):
		"""
		Helper function to populate default values in sales invoice
		"""
		if posting_date is None:
			posting_date = nowdate()

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

	def create_payment_entry(self, amount=100, posting_date=None, customer=None):
		"""
		Helper function to populate default values in payment entry
		"""
		if posting_date is None:
			posting_date = nowdate()

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

	def create_purchase_invoice(
		self, qty=1, rate=100, posting_date=None, do_not_save=False, do_not_submit=False
	):
		"""
		Helper function to populate default values in sales invoice
		"""
		if posting_date is None:
			posting_date = nowdate()

		pinv = make_purchase_invoice(
			qty=qty,
			rate=rate,
			company=self.company,
			customer=self.supplier,
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
		return pinv

	def create_purchase_order(
		self, qty=1, rate=100, posting_date=None, do_not_save=False, do_not_submit=False
	):
		"""
		Helper function to populate default values in sales invoice
		"""
		if posting_date is None:
			posting_date = nowdate()

		pord = create_purchase_order(
			qty=qty,
			rate=rate,
			company=self.company,
			customer=self.supplier,
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
		return pord

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

	def create_payment_reconciliation(self, party_is_customer=True):
		pr = frappe.new_doc("Payment Reconciliation")
		pr.company = self.company
		pr.party_type = "Customer" if party_is_customer else "Supplier"
		pr.party = self.customer if party_is_customer else self.supplier
		pr.receivable_payable_account = get_party_account(pr.party_type, pr.party, pr.company)
		pr.from_invoice_date = pr.to_invoice_date = pr.from_payment_date = pr.to_payment_date = nowdate()
		return pr

	def create_journal_entry(self, acc1=None, acc2=None, amount=0, posting_date=None, cost_center=None):
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
		for _i in range(5):
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

		# Difference amount should not be calculated for base currency accounts
		for row in pr.allocation:
			self.assertEqual(flt(row.get("difference_amount")), 0.0)

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

		# Difference amount should not be calculated for base currency accounts
		for row in pr.allocation:
			self.assertEqual(flt(row.get("difference_amount")), 0.0)

		pr.reconcile()

		# check PR tool output
		self.assertEqual(len(pr.get("invoices")), 0)
		self.assertEqual(len(pr.get("payments")), 0)

	def test_payment_against_foreign_currency_journal(self):
		transaction_date = nowdate()

		self.supplier = "_Test Supplier USD"
		self.supplier2 = make_supplier("_Test Supplier2 USD", "USD")
		amount = 100
		exc_rate1 = 80
		exc_rate2 = 83

		je = frappe.new_doc("Journal Entry")
		je.posting_date = transaction_date
		je.company = self.company
		je.user_remark = "test"
		je.multi_currency = 1
		je.set(
			"accounts",
			[
				{
					"account": self.creditors_usd,
					"party_type": "Supplier",
					"party": self.supplier,
					"exchange_rate": exc_rate1,
					"cost_center": self.cost_center,
					"credit": amount * exc_rate1,
					"credit_in_account_currency": amount,
				},
				{
					"account": self.creditors_usd,
					"party_type": "Supplier",
					"party": self.supplier2,
					"exchange_rate": exc_rate2,
					"cost_center": self.cost_center,
					"credit": amount * exc_rate2,
					"credit_in_account_currency": amount,
				},
				{
					"account": self.expense_account,
					"cost_center": self.cost_center,
					"debit": (amount * exc_rate1) + (amount * exc_rate2),
					"debit_in_account_currency": (amount * exc_rate1) + (amount * exc_rate2),
				},
			],
		)
		je.save().submit()

		pe = self.create_payment_entry(amount=amount, posting_date=transaction_date)
		pe.payment_type = "Pay"
		pe.party_type = "Supplier"
		pe.party = self.supplier
		pe.paid_to = self.creditors_usd
		pe.paid_from = self.cash
		pe.paid_amount = 8000
		pe.received_amount = 100
		pe.target_exchange_rate = exc_rate1
		pe.paid_to_account_currency = "USD"
		pe.save().submit()

		pr = self.create_payment_reconciliation(party_is_customer=False)
		pr.receivable_payable_account = self.creditors_usd
		pr.minimum_invoice_amount = pr.maximum_invoice_amount = amount
		pr.from_invoice_date = pr.to_invoice_date = transaction_date
		pr.from_payment_date = pr.to_payment_date = transaction_date

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

		# There should no difference_amount as the Journal and Payment have same exchange rate -  'exc_rate1'
		for row in pr.allocation:
			self.assertEqual(flt(row.get("difference_amount")), 0.0)

		pr.reconcile()

		# check PR tool output
		self.assertEqual(len(pr.get("invoices")), 0)
		self.assertEqual(len(pr.get("payments")), 0)

		journals = frappe.db.get_all(
			"Journal Entry Account",
			filters={"reference_type": je.doctype, "reference_name": je.name, "docstatus": 1},
			fields=["parent"],
		)
		self.assertEqual([], journals)

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

		# Difference amount should not be calculated for base currency accounts
		for row in pr.allocation:
			self.assertEqual(flt(row.get("difference_amount")), 0.0)

		pr.reconcile()

		# assert outstanding
		si.reload()
		self.assertEqual(si.status, "Paid")
		self.assertEqual(si.outstanding_amount, 0)

		# check PR tool output
		self.assertEqual(len(pr.get("invoices")), 0)
		self.assertEqual(len(pr.get("payments")), 0)

	def test_negative_debit_or_credit_journal_against_invoice(self):
		transaction_date = nowdate()
		amount = 100
		si = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)

		# credit debtors account to record a payment
		je = self.create_journal_entry(self.bank, self.debit_to, amount, transaction_date)
		je.accounts[1].party_type = "Customer"
		je.accounts[1].party = self.customer
		je.accounts[1].credit_in_account_currency = 0
		je.accounts[1].debit_in_account_currency = -1 * amount
		je.save()
		je.submit()

		pr = self.create_payment_reconciliation()

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

		# Difference amount should not be calculated for base currency accounts
		for row in pr.allocation:
			self.assertEqual(flt(row.get("difference_amount")), 0.0)

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

		# Difference amount should not be calculated for base currency accounts
		for row in pr.allocation:
			self.assertEqual(flt(row.get("difference_amount")), 0.0)

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

		# Cr Note and Invoice are of the same currency. There shouldn't any difference amount.
		for row in pr.allocation:
			self.assertEqual(flt(row.get("difference_amount")), 0.0)

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

	def test_invoice_status_after_cr_note_cancellation(self):
		# This test case is made after the 'always standalone Credit/Debit notes' feature is introduced
		transaction_date = nowdate()
		amount = 100

		si = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)

		cr_note = self.create_sales_invoice(
			qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		cr_note.is_return = 1
		cr_note.return_against = si.name
		cr_note = cr_note.save().submit()

		pr = self.create_payment_reconciliation()

		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		pr.get_unreconciled_entries()
		self.assertEqual(pr.get("invoices"), [])
		self.assertEqual(pr.get("payments"), [])

		journals = frappe.db.get_all(
			"Journal Entry",
			filters={
				"is_system_generated": 1,
				"docstatus": 1,
				"voucher_type": "Credit Note",
				"reference_type": si.doctype,
				"reference_name": si.name,
			},
			pluck="name",
		)
		self.assertEqual(len(journals), 1)

		# assert status and outstanding
		si.reload()
		self.assertEqual(si.status, "Credit Note Issued")
		self.assertEqual(si.outstanding_amount, 0)

		cr_note.reload()
		cr_note.cancel()
		# 'Credit Note' Journal should be auto cancelled
		journals = frappe.db.get_all(
			"Journal Entry",
			filters={
				"is_system_generated": 1,
				"docstatus": 1,
				"voucher_type": "Credit Note",
				"reference_type": si.doctype,
				"reference_name": si.name,
			},
			pluck="name",
		)
		self.assertEqual(len(journals), 0)
		# assert status and outstanding
		si.reload()
		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(si.outstanding_amount, 100)

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

		# Cr Note and Invoice are of the same currency. There shouldn't any difference amount.
		for row in pr.allocation:
			self.assertEqual(flt(row.get("difference_amount")), 0.0)

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

		pay = self.create_payment_entry(amount=amount, posting_date=transaction_date, customer=self.customer3)
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
		total_credit_amount = frappe.db.get_all(
			"Journal Entry Account",
			{"account": self.debtors_eur, "docstatus": 1, "reference_name": si.name},
			[{"SUM": "credit", "as": "amount"}],
			group_by="reference_name",
		)[0].amount

		# total credit includes the exchange gain/loss amount
		self.assertEqual(flt(total_credit_amount, 2), 8500)

		jea_parent = frappe.db.get_all(
			"Journal Entry Account",
			filters={"account": self.debtors_eur, "docstatus": 1, "reference_name": si.name, "credit": 500},
			fields=["parent"],
		)[0]
		self.assertEqual(
			frappe.db.get_value("Journal Entry", jea_parent.parent, "voucher_type"), "Exchange Gain Or Loss"
		)

	def test_difference_amount_via_negative_debit_or_credit_journal_entry(self):
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
		je1.accounts[0].credit_in_account_currency = -8000
		je1.accounts[0].credit = -8000
		je1.accounts[0].debit_in_account_currency = 0
		je1.accounts[0].debit = 0
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
		je2.accounts[0].credit_in_account_currency = -16000
		je2.accounts[0].credit = -16000
		je2.accounts[0].debit_in_account_currency = 0
		je2.accounts[0].debit = 0
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
		total_credit_amount = frappe.db.get_all(
			"Journal Entry Account",
			{"account": self.debtors_eur, "docstatus": 1, "reference_name": si.name},
			[{"SUM": "credit", "as": "amount"}],
			group_by="reference_name",
		)[0].amount

		# total credit includes the exchange gain/loss amount
		self.assertEqual(flt(total_credit_amount, 2), 8500)

		jea_parent = frappe.db.get_all(
			"Journal Entry Account",
			filters={"account": self.debtors_eur, "docstatus": 1, "reference_name": si.name, "credit": 500},
			fields=["parent"],
		)[0]
		self.assertEqual(
			frappe.db.get_value("Journal Entry", jea_parent.parent, "voucher_type"), "Exchange Gain Or Loss"
		)

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
		si1 = self.create_sales_invoice(qty=1, rate=rate, posting_date=transaction_date, do_not_submit=True)
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
		si2 = self.create_sales_invoice(qty=1, rate=rate, posting_date=transaction_date, do_not_submit=True)
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

	@IntegrationTestCase.change_settings(
		"Accounts Settings",
		{
			"allow_multi_currency_invoices_against_single_party_account": 1,
		},
	)
	def test_no_difference_amount_for_base_currency_accounts(self):
		# Make Sale Invoice
		si = self.create_sales_invoice(
			qty=1, rate=1, posting_date=nowdate(), do_not_save=True, do_not_submit=True
		)
		si.customer = self.customer
		si.currency = "EUR"
		si.conversion_rate = 85
		si.debit_to = self.debit_to
		si.save().submit()

		# Make payment using Payment Entry
		pe1 = create_payment_entry(
			company=self.company,
			payment_type="Receive",
			party_type="Customer",
			party=self.customer,
			paid_from=self.debit_to,
			paid_to=self.bank,
			paid_amount=100,
		)

		pe1.save()
		pe1.submit()

		pr = self.create_payment_reconciliation()
		pr.party = self.customer
		pr.receivable_payable_account = self.debit_to
		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)

		invoices = [x.as_dict() for x in pr.invoices]
		payments = [pr.payments[0].as_dict()]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

		self.assertEqual(pr.allocation[0].allocated_amount, 85)
		self.assertEqual(pr.allocation[0].difference_amount, 0)

		pr.reconcile()
		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		# No Exchange Gain/Loss journal should be generated
		exc_gain_loss_journals = frappe.db.get_all(
			"Journal Entry Account",
			filters={"reference_type": si.doctype, "reference_name": si.name, "docstatus": 1},
			fields=["parent"],
		)
		self.assertEqual(exc_gain_loss_journals, [])

	def test_reconciliation_purchase_invoice_against_return(self):
		self.supplier = "_Test Supplier USD"
		pi = self.create_purchase_invoice(qty=5, rate=50, do_not_submit=True)
		pi.supplier = self.supplier
		pi.currency = "USD"
		pi.conversion_rate = 50
		pi.credit_to = self.creditors_usd
		pi.save().submit()

		pi_return = frappe.get_doc(pi.as_dict())
		pi_return.name = None
		pi_return.docstatus = 0
		pi_return.is_return = 1
		pi_return.conversion_rate = 80
		pi_return.items[0].qty = -pi_return.items[0].qty
		pi_return.submit()

		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = self.company
		pr.party_type = "Supplier"
		pr.party = self.supplier
		pr.receivable_payable_account = self.creditors_usd
		pr.from_invoice_date = pr.to_invoice_date = pr.from_payment_date = pr.to_payment_date = nowdate()
		pr.get_unreconciled_entries()

		invoices = []
		payments = []
		for invoice in pr.invoices:
			if invoice.invoice_number == pi.name:
				invoices.append(invoice.as_dict())
				break

		for payment in pr.payments:
			if payment.reference_name == pi_return.name:
				payments.append(payment.as_dict())
				break

		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

		# Should not raise frappe.exceptions.ValidationError: Total Debit must be equal to Total Credit.
		pr.reconcile()

	def test_reconciliation_from_purchase_order_to_multiple_invoices(self):
		"""
		Reconciling advance payment from PO/SO to multiple invoices should not cause overallocation
		"""

		self.supplier = "_Test Supplier"

		pi1 = self.create_purchase_invoice(qty=10, rate=100)
		pi2 = self.create_purchase_invoice(qty=10, rate=100)
		po = self.create_purchase_order(qty=20, rate=100)
		pay = get_payment_entry(po.doctype, po.name)
		# Overpay Puchase Order
		pay.paid_amount = 3000
		pay.save().submit()
		# assert total allocated and unallocated before reconciliation
		self.assertEqual(
			(
				pay.references[0].reference_doctype,
				pay.references[0].reference_name,
				pay.references[0].allocated_amount,
			),
			(po.doctype, po.name, 2000),
		)
		self.assertEqual(pay.total_allocated_amount, 2000)
		self.assertEqual(pay.unallocated_amount, 1000)
		self.assertEqual(pay.difference_amount, 0)

		pr = self.create_payment_reconciliation(party_is_customer=False)
		pr.get_unreconciled_entries()

		self.assertEqual(len(pr.invoices), 2)
		self.assertEqual(len(pr.payments), 2)

		for x in pr.payments:
			self.assertEqual((x.reference_type, x.reference_name), (pay.doctype, pay.name))

		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		# partial allocation on pi1 and full allocate on pi2
		pr.allocation[0].allocated_amount = 100
		pr.reconcile()

		# assert references and total allocated and unallocated amount
		pay.reload()
		self.assertEqual(len(pay.references), 3)
		self.assertEqual(
			(
				pay.references[0].reference_doctype,
				pay.references[0].reference_name,
				pay.references[0].allocated_amount,
			),
			(po.doctype, po.name, 900),
		)
		self.assertEqual(
			(
				pay.references[1].reference_doctype,
				pay.references[1].reference_name,
				pay.references[1].allocated_amount,
			),
			(pi1.doctype, pi1.name, 100),
		)
		self.assertEqual(
			(
				pay.references[2].reference_doctype,
				pay.references[2].reference_name,
				pay.references[2].allocated_amount,
			),
			(pi2.doctype, pi2.name, 1000),
		)
		self.assertEqual(pay.total_allocated_amount, 2000)
		self.assertEqual(pay.unallocated_amount, 1000)
		self.assertEqual(pay.difference_amount, 0)

		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 2)

		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		# assert references and total allocated and unallocated amount
		pay.reload()
		self.assertEqual(len(pay.references), 3)
		# PO references should be removed now
		self.assertEqual(
			(
				pay.references[0].reference_doctype,
				pay.references[0].reference_name,
				pay.references[0].allocated_amount,
			),
			(pi1.doctype, pi1.name, 100),
		)
		self.assertEqual(
			(
				pay.references[1].reference_doctype,
				pay.references[1].reference_name,
				pay.references[1].allocated_amount,
			),
			(pi2.doctype, pi2.name, 1000),
		)
		self.assertEqual(
			(
				pay.references[2].reference_doctype,
				pay.references[2].reference_name,
				pay.references[2].allocated_amount,
			),
			(pi1.doctype, pi1.name, 900),
		)
		self.assertEqual(pay.total_allocated_amount, 2000)
		self.assertEqual(pay.unallocated_amount, 1000)
		self.assertEqual(pay.difference_amount, 0)

	def test_rounding_of_unallocated_amount(self):
		self.supplier = "_Test Supplier USD"
		pi = self.create_purchase_invoice(qty=1, rate=10, do_not_submit=True)
		pi.supplier = self.supplier
		pi.currency = "USD"
		pi.conversion_rate = 80
		pi.credit_to = self.creditors_usd
		pi.save().submit()

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.target_exchange_rate = 78.726500000
		pe.received_amount = 26.75
		pe.paid_amount = 2105.93
		pe.references = []
		pe.save().submit()

		# unallocated_amount will have some rounding loss - 26.749950
		self.assertNotEqual(pe.unallocated_amount, 26.75)

		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = self.company
		pr.party_type = "Supplier"
		pr.party = self.supplier
		pr.receivable_payable_account = self.creditors_usd
		pr.from_invoice_date = pr.to_invoice_date = pr.from_payment_date = pr.to_payment_date = nowdate()
		pr.get_unreconciled_entries()

		invoices = [invoice.as_dict() for invoice in pr.invoices]
		payments = [payment.as_dict() for payment in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

		# Should not raise frappe.exceptions.ValidationError: Payment Entry has been modified after you pulled it. Please pull it again.
		pr.reconcile()

	def test_reverse_payment_against_payment_for_supplier(self):
		"""
		Reconcile a payment against a reverse payment, for a supplier.
		"""
		self.supplier = "_Test Supplier"
		amount = 4000

		pe = self.create_payment_entry(amount=amount)
		pe.party_type = "Supplier"
		pe.party = self.supplier
		pe.payment_type = "Pay"
		pe.paid_from = self.cash
		pe.paid_to = self.creditors
		pe.save().submit()

		reverse_pe = self.create_payment_entry(amount=amount)
		reverse_pe.party_type = "Supplier"
		reverse_pe.party = self.supplier
		reverse_pe.payment_type = "Receive"
		reverse_pe.paid_from = self.creditors
		reverse_pe.paid_to = self.cash
		reverse_pe.save().submit()

		pr = self.create_payment_reconciliation(party_is_customer=False)
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		self.assertEqual(pr.invoices[0].invoice_number, reverse_pe.name)
		self.assertEqual(pr.payments[0].reference_name, pe.name)

		invoices = [invoice.as_dict() for invoice in pr.invoices]
		payments = [payment.as_dict() for payment in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		pe.reload()
		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.references[0].exchange_rate, 1)
		# There should not be any Exc Gain/Loss
		self.assertEqual(pe.references[0].exchange_gain_loss, 0)
		self.assertEqual(pe.references[0].reference_name, reverse_pe.name)

		journals = frappe.db.get_all(
			"Journal Entry",
			filters={
				"voucher_type": "Exchange Gain Or Loss",
				"reference_type": "Payment Entry",
				"reference_name": ("in", [pe.name, reverse_pe.name]),
			},
		)
		# There should be no Exchange Gain/Loss created
		self.assertEqual(journals, [])

	def test_advance_reverse_payment_against_payment_for_supplier(self):
		"""
		Reconcile an Advance payment against reverse payment, for a supplier.
		"""
		frappe.db.set_value(
			"Company",
			self.company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_paid_account": self.advance_payable_account,
			},
		)

		self.supplier = "_Test Supplier"
		amount = 4000

		pe = self.create_payment_entry(amount=amount)
		pe.party_type = "Supplier"
		pe.party = self.supplier
		pe.payment_type = "Pay"
		pe.paid_from = self.cash
		pe.paid_to = self.advance_payable_account
		pe.save().submit()

		reverse_pe = self.create_payment_entry(amount=amount)
		reverse_pe.party_type = "Supplier"
		reverse_pe.party = self.supplier
		reverse_pe.payment_type = "Receive"
		reverse_pe.paid_from = self.advance_payable_account
		reverse_pe.paid_to = self.cash
		reverse_pe.save().submit()

		pr = self.create_payment_reconciliation(party_is_customer=False)
		pr.default_advance_account = self.advance_payable_account
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		self.assertEqual(pr.invoices[0].invoice_number, reverse_pe.name)
		self.assertEqual(pr.payments[0].reference_name, pe.name)

		invoices = [invoice.as_dict() for invoice in pr.invoices]
		payments = [payment.as_dict() for payment in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		pe.reload()
		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.references[0].exchange_rate, 1)
		# There should not be any Exc Gain/Loss
		self.assertEqual(pe.references[0].exchange_gain_loss, 0)
		self.assertEqual(pe.references[0].reference_name, reverse_pe.name)

		journals = frappe.db.get_all(
			"Journal Entry",
			filters={
				"voucher_type": "Exchange Gain Or Loss",
				"reference_type": "Payment Entry",
				"reference_name": ("in", [pe.name, reverse_pe.name]),
			},
		)
		# There should be no Exchange Gain/Loss created
		self.assertEqual(journals, [])

		# Assert Ledger Entries
		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pe.name},
			fields=["account", "voucher_no", "against_voucher", "debit", "credit"],
			order_by="account, against_voucher, debit",
		)
		expected_gle = [
			{
				"account": self.advance_payable_account,
				"voucher_no": pe.name,
				"against_voucher": pe.name,
				"debit": 0.0,
				"credit": amount,
			},
			{
				"account": self.advance_payable_account,
				"voucher_no": pe.name,
				"against_voucher": pe.name,
				"debit": amount,
				"credit": 0.0,
			},
			{
				"account": self.advance_payable_account,
				"voucher_no": pe.name,
				"against_voucher": reverse_pe.name,
				"debit": amount,
				"credit": 0.0,
			},
			{
				"account": "Cash - _PR",
				"voucher_no": pe.name,
				"against_voucher": None,
				"debit": 0.0,
				"credit": amount,
			},
		]
		self.assertEqual(gl_entries, expected_gle)
		pl_entries = frappe.db.get_all(
			"Payment Ledger Entry",
			filters={"voucher_no": pe.name},
			fields=["account", "voucher_no", "against_voucher_no", "amount"],
			order_by="account, against_voucher_no, amount",
		)
		expected_ple = [
			{
				"account": self.advance_payable_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": -amount,
			},
			{
				"account": self.advance_payable_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": amount,
			},
			{
				"account": self.advance_payable_account,
				"voucher_no": pe.name,
				"against_voucher_no": reverse_pe.name,
				"amount": -amount,
			},
		]
		self.assertEqual(pl_entries, expected_ple)

	def test_advance_payment_reconciliation_date(self):
		frappe.db.set_value(
			"Company",
			self.company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_paid_account": self.advance_payable_account,
				"reconciliation_takes_effect_on": "Advance Payment Date",
			},
		)

		self.supplier = "_Test Supplier"
		amount = 1500

		pe = self.create_payment_entry(amount=amount)
		pe.posting_date = add_days(nowdate(), -1)
		pe.party_type = "Supplier"
		pe.party = self.supplier
		pe.payment_type = "Pay"
		pe.paid_from = self.cash
		pe.paid_to = self.advance_payable_account
		pe.save().submit()

		pi = self.create_purchase_invoice(qty=10, rate=100)
		self.assertNotEqual(pe.posting_date, pi.posting_date)

		pr = self.create_payment_reconciliation(party_is_customer=False)
		pr.default_advance_account = self.advance_payable_account
		pr.from_payment_date = pe.posting_date
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [invoice.as_dict() for invoice in pr.invoices]
		payments = [payment.as_dict() for payment in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		# Assert Ledger Entries
		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pe.name, "is_cancelled": 0, "posting_date": pe.posting_date},
		)
		self.assertEqual(len(gl_entries), 4)
		pl_entries = frappe.db.get_all(
			"Payment Ledger Entry",
			filters={"voucher_no": pe.name, "delinked": 0, "posting_date": pe.posting_date},
		)
		self.assertEqual(len(pl_entries), 3)

	def test_advance_payment_reconciliation_date_for_older_date(self):
		old_settings = frappe.db.get_value(
			"Company",
			self.company,
			[
				"reconciliation_takes_effect_on",
				"default_advance_paid_account",
				"book_advance_payments_in_separate_party_account",
			],
			as_dict=True,
		)
		frappe.db.set_value(
			"Company",
			self.company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_paid_account": self.advance_payable_account,
				"reconciliation_takes_effect_on": "Oldest Of Invoice Or Advance",
			},
		)

		self.supplier = "_Test Supplier"

		pi1 = self.create_purchase_invoice(qty=10, rate=100)
		po = self.create_purchase_order(qty=10, rate=100)

		pay = get_payment_entry(po.doctype, po.name)
		pay.paid_amount = 1000
		pay.save().submit()

		pr = frappe.new_doc("Payment Reconciliation")
		pr.company = self.company
		pr.party_type = "Supplier"
		pr.party = self.supplier
		pr.receivable_payable_account = get_party_account(pr.party_type, pr.party, pr.company)
		pr.default_advance_account = self.advance_payable_account
		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.allocation[0].allocated_amount = 100
		pr.reconcile()

		pay.reload()
		self.assertEqual(getdate(pay.references[0].reconcile_effect_on), getdate(pi1.posting_date))

		# test setting of date if not available
		frappe.db.set_value("Payment Entry Reference", pay.references[1].name, "reconcile_effect_on", None)
		pay.reload()
		pay.cancel()

		pay.reload()
		pi1.reload()
		po.reload()

		self.assertEqual(getdate(pay.references[0].reconcile_effect_on), getdate(pi1.posting_date))
		pi1.cancel()
		po.cancel()

		frappe.db.set_value("Company", self.company, old_settings)

	def test_advance_payment_reconciliation_against_journal_for_customer(self):
		frappe.db.set_value(
			"Company",
			self.company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_received_account": self.advance_receivable_account,
				"reconciliation_takes_effect_on": "Oldest Of Invoice Or Advance",
			},
		)
		amount = 200.0
		je = self.create_journal_entry(self.debit_to, self.bank, amount)
		je.accounts[0].cost_center = self.main_cc.name
		je.accounts[0].party_type = "Customer"
		je.accounts[0].party = self.customer
		je.accounts[1].cost_center = self.main_cc.name
		je = je.save().submit()

		pe = self.create_payment_entry(amount=amount).save().submit()

		pr = self.create_payment_reconciliation()
		pr.default_advance_account = self.advance_receivable_account
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [invoice.as_dict() for invoice in pr.invoices]
		payments = [payment.as_dict() for payment in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		# Assert Ledger Entries
		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pe.name, "is_cancelled": 0},
		)
		self.assertEqual(len(gl_entries), 4)
		pl_entries = frappe.db.get_all(
			"Payment Ledger Entry",
			filters={"voucher_no": pe.name, "delinked": 0},
		)
		self.assertEqual(len(pl_entries), 3)

		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pe.name, "is_cancelled": 0},
			fields=["account", "voucher_no", "against_voucher", "debit", "credit"],
			order_by="account, against_voucher, debit",
		)
		expected_gle = [
			{
				"account": self.advance_receivable_account,
				"voucher_no": pe.name,
				"against_voucher": pe.name,
				"debit": 0.0,
				"credit": amount,
			},
			{
				"account": self.advance_receivable_account,
				"voucher_no": pe.name,
				"against_voucher": pe.name,
				"debit": amount,
				"credit": 0.0,
			},
			{
				"account": self.debit_to,
				"voucher_no": pe.name,
				"against_voucher": je.name,
				"debit": 0.0,
				"credit": amount,
			},
			{
				"account": self.bank,
				"voucher_no": pe.name,
				"against_voucher": None,
				"debit": amount,
				"credit": 0.0,
			},
		]
		self.assertEqual(gl_entries, expected_gle)

		pl_entries = frappe.db.get_all(
			"Payment Ledger Entry",
			filters={"voucher_no": pe.name},
			fields=["account", "voucher_no", "against_voucher_no", "amount"],
			order_by="account, against_voucher_no, amount",
		)
		expected_ple = [
			{
				"account": self.advance_receivable_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": -amount,
			},
			{
				"account": self.advance_receivable_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": amount,
			},
			{
				"account": self.debit_to,
				"voucher_no": pe.name,
				"against_voucher_no": je.name,
				"amount": -amount,
			},
		]
		self.assertEqual(pl_entries, expected_ple)

	def test_advance_payment_reconciliation_against_journal_for_supplier(self):
		self.supplier = make_supplier("_Test Supplier")
		frappe.db.set_value(
			"Company",
			self.company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_paid_account": self.advance_payable_account,
				"reconciliation_takes_effect_on": "Oldest Of Invoice Or Advance",
			},
		)
		amount = 200.0
		je = self.create_journal_entry(self.creditors, self.bank, -amount)
		je.accounts[0].cost_center = self.main_cc.name
		je.accounts[0].party_type = "Supplier"
		je.accounts[0].party = self.supplier
		je.accounts[1].cost_center = self.main_cc.name
		je = je.save().submit()

		pe = self.create_payment_entry(amount=amount)
		pe.payment_type = "Pay"
		pe.party_type = "Supplier"
		pe.paid_from = self.bank
		pe.paid_to = self.creditors
		pe.party = self.supplier
		pe.save().submit()

		pr = self.create_payment_reconciliation(party_is_customer=False)
		pr.default_advance_account = self.advance_payable_account
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [invoice.as_dict() for invoice in pr.invoices]
		payments = [payment.as_dict() for payment in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		# Assert Ledger Entries
		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pe.name, "is_cancelled": 0},
		)
		self.assertEqual(len(gl_entries), 4)
		pl_entries = frappe.db.get_all(
			"Payment Ledger Entry",
			filters={"voucher_no": pe.name, "delinked": 0},
		)
		self.assertEqual(len(pl_entries), 3)

		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pe.name, "is_cancelled": 0},
			fields=["account", "voucher_no", "against_voucher", "debit", "credit"],
			order_by="account, against_voucher, debit",
		)
		expected_gle = [
			{
				"account": self.advance_payable_account,
				"voucher_no": pe.name,
				"against_voucher": pe.name,
				"debit": 0.0,
				"credit": amount,
			},
			{
				"account": self.advance_payable_account,
				"voucher_no": pe.name,
				"against_voucher": pe.name,
				"debit": amount,
				"credit": 0.0,
			},
			{
				"account": self.creditors,
				"voucher_no": pe.name,
				"against_voucher": je.name,
				"debit": amount,
				"credit": 0.0,
			},
			{
				"account": self.bank,
				"voucher_no": pe.name,
				"against_voucher": None,
				"debit": 0.0,
				"credit": amount,
			},
		]
		self.assertEqual(gl_entries, expected_gle)

		pl_entries = frappe.db.get_all(
			"Payment Ledger Entry",
			filters={"voucher_no": pe.name},
			fields=["account", "voucher_no", "against_voucher_no", "amount"],
			order_by="account, against_voucher_no, amount",
		)
		expected_ple = [
			{
				"account": self.advance_payable_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": -amount,
			},
			{
				"account": self.advance_payable_account,
				"voucher_no": pe.name,
				"against_voucher_no": pe.name,
				"amount": amount,
			},
			{
				"account": self.creditors,
				"voucher_no": pe.name,
				"against_voucher_no": je.name,
				"amount": -amount,
			},
		]
		self.assertEqual(pl_entries, expected_ple)

	def test_cr_note_payment_limit_filter(self):
		transaction_date = nowdate()
		amount = 100

		for _ in range(6):
			self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
			cr_note = self.create_sales_invoice(
				qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
			)
			cr_note.is_return = 1
			cr_note = cr_note.save().submit()

		pr = self.create_payment_reconciliation()

		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 6)
		self.assertEqual(len(pr.payments), 6)
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		pr.get_unreconciled_entries()
		self.assertEqual(pr.get("invoices"), [])
		self.assertEqual(pr.get("payments"), [])

		self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		cr_note = self.create_sales_invoice(
			qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		cr_note.is_return = 1
		cr_note = cr_note.save().submit()

		# Limit should not affect in fetching the unallocated cr_note
		pr.invoice_limit = 5
		pr.payment_limit = 5
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)

	def test_reconciliation_on_closed_period_payment(self):
		# create backdated fiscal year
		first_fy_start_date = frappe.db.get_value(
			"Fiscal Year", {"disabled": 0}, [{"MIN": "year_start_date"}]
		)
		prev_fy_start_date = add_years(first_fy_start_date, -1)
		prev_fy_end_date = add_days(first_fy_start_date, -1)
		create_fiscal_year(
			company=self.company, year_start_date=prev_fy_start_date, year_end_date=prev_fy_end_date
		)

		# make journal entry for previous year
		je_1 = frappe.new_doc("Journal Entry")
		je_1.posting_date = add_days(prev_fy_start_date, 20)
		je_1.company = self.company
		je_1.user_remark = "test"
		je_1.set(
			"accounts",
			[
				{
					"account": self.debit_to,
					"cost_center": self.cost_center,
					"party_type": "Customer",
					"party": self.customer,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": 1000,
				},
				{
					"account": self.bank,
					"cost_center": self.sub_cc.name,
					"credit_in_account_currency": 0,
					"debit_in_account_currency": 500,
				},
				{
					"account": self.cash,
					"cost_center": self.sub_cc.name,
					"credit_in_account_currency": 0,
					"debit_in_account_currency": 500,
				},
			],
		)
		je_1.submit()

		# make period closing voucher
		pcv = make_period_closing_voucher(
			company=self.company, cost_center=self.cost_center, posting_date=prev_fy_end_date
		)
		pcv.reload()
		# check if period closing voucher is completed
		self.assertEqual(pcv.gle_processing_status, "Completed")

		# make journal entry for active year
		je_2 = self.create_journal_entry(
			acc1=self.debit_to, acc2=self.income_account, amount=1000, posting_date=today()
		)
		je_2.accounts[0].party_type = "Customer"
		je_2.accounts[0].party = self.customer
		je_2.submit()

		# process reconciliation on closed period payment
		pr = self.create_payment_reconciliation(party_is_customer=True)
		pr.from_invoice_date = pr.to_invoice_date = pr.from_payment_date = pr.to_payment_date = None
		pr.get_unreconciled_entries()
		invoices = [invoice.as_dict() for invoice in pr.invoices]
		payments = [payment.as_dict() for payment in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		je_1.reload()
		je_2.reload()

		# check whether the payment reconciliation is done on the closed period
		self.assertEqual(pr.get("invoices"), [])
		self.assertEqual(pr.get("payments"), [])

	def test_advance_reconciliation_effect_on_same_date(self):
		frappe.db.set_value(
			"Company",
			self.company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_received_account": self.advance_receivable_account,
				"reconciliation_takes_effect_on": "Reconciliation Date",
			},
		)
		inv_date = convert_to_date(add_days(nowdate(), -1))
		adv_date = convert_to_date(add_days(nowdate(), -2))

		si = self.create_sales_invoice(posting_date=inv_date, qty=1, rate=200)
		pe = self.create_payment_entry(posting_date=adv_date, amount=80).save().submit()

		pr = self.create_payment_reconciliation()
		pr.from_invoice_date = add_days(nowdate(), -1)
		pr.to_invoice_date = nowdate()
		pr.from_payment_date = add_days(nowdate(), -2)
		pr.to_payment_date = nowdate()
		pr.default_advance_account = self.advance_receivable_account

		# reconcile multiple payments against invoice
		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))

		# Difference amount should not be calculated for base currency accounts
		for row in pr.allocation:
			self.assertEqual(flt(row.get("difference_amount")), 0.0)

		pr.reconcile()

		si.reload()
		self.assertEqual(si.status, "Partly Paid")
		# check PR tool output post reconciliation
		self.assertEqual(len(pr.get("invoices")), 1)
		self.assertEqual(pr.get("invoices")[0].get("outstanding_amount"), 120)
		self.assertEqual(pr.get("payments"), [])

		# Assert Ledger Entries
		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pe.name},
			fields=["account", "posting_date", "voucher_no", "against_voucher", "debit", "credit"],
			order_by="account, against_voucher, debit",
		)

		expected_gl = [
			{
				"account": self.advance_receivable_account,
				"posting_date": adv_date,
				"voucher_no": pe.name,
				"against_voucher": pe.name,
				"debit": 0.0,
				"credit": 80.0,
			},
			{
				"account": self.advance_receivable_account,
				"posting_date": convert_to_date(nowdate()),
				"voucher_no": pe.name,
				"against_voucher": pe.name,
				"debit": 80.0,
				"credit": 0.0,
			},
			{
				"account": self.debit_to,
				"posting_date": convert_to_date(nowdate()),
				"voucher_no": pe.name,
				"against_voucher": si.name,
				"debit": 0.0,
				"credit": 80.0,
			},
			{
				"account": self.bank,
				"posting_date": adv_date,
				"voucher_no": pe.name,
				"against_voucher": None,
				"debit": 80.0,
				"credit": 0.0,
			},
		]

		self.assertEqual(expected_gl, gl_entries)

		# cancel PE
		pe.reload()
		pe.cancel()
		pr.get_unreconciled_entries()
		# check PR tool output
		self.assertEqual(len(pr.get("invoices")), 1)
		self.assertEqual(len(pr.get("payments")), 0)
		self.assertEqual(pr.get("invoices")[0].get("outstanding_amount"), 200)

	def test_partial_advance_payment_with_closed_fiscal_year(self):
		"""
		Test Advance Payment partial reconciliation before period closing and partial after period closing
		"""
		default_settings = frappe.db.get_value(
			"Company",
			self.company,
			[
				"book_advance_payments_in_separate_party_account",
				"default_advance_paid_account",
				"reconciliation_takes_effect_on",
			],
			as_dict=True,
		)
		first_fy_start_date = frappe.db.get_value(
			"Fiscal Year", {"disabled": 0}, [{"MIN": "year_start_date"}]
		)
		prev_fy_start_date = add_years(first_fy_start_date, -1)
		prev_fy_end_date = add_days(first_fy_start_date, -1)

		create_fiscal_year(
			company=self.company, year_start_date=prev_fy_start_date, year_end_date=prev_fy_end_date
		)

		frappe.db.set_value(
			"Company",
			self.company,
			{
				"book_advance_payments_in_separate_party_account": 1,
				"default_advance_paid_account": self.advance_payable_account,
				"reconciliation_takes_effect_on": "Oldest Of Invoice Or Advance",
			},
		)

		self.supplier = "_Test Supplier"

		# Create advance payment of 1000 (previous FY)
		pe = self.create_payment_entry(amount=1000, posting_date=prev_fy_start_date)
		pe.party_type = "Supplier"
		pe.party = self.supplier
		pe.payment_type = "Pay"
		pe.paid_from = self.cash
		pe.paid_to = self.advance_payable_account
		pe.save().submit()

		# Create purchase invoice of 600 (previous FY)
		pi1 = self.create_purchase_invoice(qty=1, rate=600, do_not_submit=True)
		pi1.posting_date = prev_fy_start_date
		pi1.set_posting_time = 1
		pi1.supplier = self.supplier
		pi1.credit_to = self.creditors
		pi1.save().submit()

		# Reconcile advance payment
		pr = self.create_payment_reconciliation(party_is_customer=False)
		pr.party = self.supplier
		pr.receivable_payable_account = self.creditors
		pr.default_advance_account = self.advance_payable_account
		pr.from_invoice_date = pr.to_invoice_date = pi1.posting_date
		pr.from_payment_date = pr.to_payment_date = pe.posting_date
		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.invoices if x.invoice_number == pi1.name]
		payments = [x.as_dict() for x in pr.payments if x.reference_name == pe.name]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		# Verify partial reconciliation
		pe.reload()
		pi1.reload()

		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.references[0].allocated_amount, 600)
		self.assertEqual(flt(pe.unallocated_amount), 400)

		self.assertEqual(pi1.outstanding_amount, 0)
		self.assertEqual(pi1.status, "Paid")

		# Close accounting period for March (previous FY)
		pcv = make_period_closing_voucher(
			company=self.company, cost_center=self.cost_center, posting_date=prev_fy_end_date
		)
		pcv.reload()
		self.assertEqual(pcv.gle_processing_status, "Completed")

		# Change reconciliation setting to "Reconciliation Date"
		frappe.db.set_value(
			"Company",
			self.company,
			"reconciliation_takes_effect_on",
			"Reconciliation Date",
		)

		# Create new purchase invoice for 400 in new fiscal year
		pi2 = self.create_purchase_invoice(qty=1, rate=400, do_not_submit=True)
		pi2.posting_date = today()
		pi2.set_posting_time = 1
		pi2.supplier = self.supplier
		pi2.currency = "INR"
		pi2.credit_to = self.creditors
		pi2.save()
		pi2.submit()

		# Allocate 600 from advance payment to purchase invoice
		pr = self.create_payment_reconciliation(party_is_customer=False)
		pr.party = self.supplier
		pr.receivable_payable_account = self.creditors
		pr.default_advance_account = self.advance_payable_account
		pr.from_invoice_date = pr.to_invoice_date = pi2.posting_date
		pr.from_payment_date = pr.to_payment_date = pe.posting_date
		pr.get_unreconciled_entries()
		invoices = [x.as_dict() for x in pr.invoices if x.invoice_number == pi2.name]
		payments = [x.as_dict() for x in pr.payments if x.reference_name == pe.name]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		pe.reload()
		pi2.reload()

		# Assert advance payment is fully allocated
		self.assertEqual(len(pe.references), 2)
		self.assertEqual(flt(pe.unallocated_amount), 0)

		# Assert new invoice is fully paid
		self.assertEqual(pi2.outstanding_amount, 0)
		self.assertEqual(pi2.status, "Paid")

		# Verify reconciliation dates are correct based on company setting
		self.assertEqual(getdate(pe.references[0].reconcile_effect_on), getdate(pi1.posting_date))
		self.assertEqual(getdate(pe.references[1].reconcile_effect_on), getdate(pi2.posting_date))

		frappe.db.set_value("Company", self.company, default_settings)


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


def make_supplier(supplier_name, currency=None):
	if not frappe.db.exists("Supplier", supplier_name):
		supplier = frappe.new_doc("Supplier")
		supplier.supplier_name = supplier_name
		supplier.type = "Individual"

		if currency:
			supplier.default_currency = currency
		supplier.save()
		return supplier.name
	else:
		return supplier_name


def create_fiscal_year(company, year_start_date, year_end_date):
	fy_docname = frappe.db.exists(
		"Fiscal Year", {"year_start_date": year_start_date, "year_end_date": year_end_date}
	)
	if not fy_docname:
		fy_doc = frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": f"{getdate(year_start_date).year}-{getdate(year_end_date).year}",
				"year_start_date": year_start_date,
				"year_end_date": year_end_date,
				"companies": [{"company": company}],
			}
		).save()
		return fy_doc
	else:
		fy_doc = frappe.get_doc("Fiscal Year", fy_docname)
		if not frappe.db.exists("Fiscal Year Company", {"parent": fy_docname, "company": company}):
			fy_doc.append("companies", {"company": company})
			fy_doc.save()
		return fy_doc


def make_period_closing_voucher(company, cost_center, posting_date=None, submit=True):
	from erpnext.accounts.doctype.account.test_account import create_account

	parent_account = frappe.db.get_value(
		"Account", {"company": company, "account_name": "Current Liabilities", "is_group": 1}, "name"
	)
	surplus_account = create_account(
		account_name="Reserve and Surplus",
		is_group=0,
		company=company,
		root_type="Liability",
		report_type="Balance Sheet",
		account_currency="INR",
		parent_account=parent_account,
		doctype="Account",
	)
	fy = get_fiscal_year(posting_date, company=company)
	pcv = frappe.get_doc(
		{
			"doctype": "Period Closing Voucher",
			"transaction_date": posting_date or today(),
			"period_start_date": fy[1],
			"period_end_date": fy[2],
			"company": company,
			"fiscal_year": fy[0],
			"cost_center": cost_center,
			"closing_account_head": surplus_account,
			"remarks": "test",
		}
	)
	pcv.insert()
	if submit:
		pcv.submit()

	return pcv
