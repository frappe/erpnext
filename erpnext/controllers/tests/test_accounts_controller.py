# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from datetime import datetime

import frappe
from frappe import qb
from frappe.query_builder.functions import Sum
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate
from frappe.utils.data import getdate as convert_to_date

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.party import get_party_account
from erpnext.buying.doctype.purchase_order.test_purchase_order import (
	create_purchase_order,
	prepare_data_for_internal_transfer,
)
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.stock.doctype.item.test_item import create_item


def make_customer(customer_name, currency=None):
	if not frappe.db.exists("Customer", customer_name):
		customer = frappe.new_doc("Customer")
		customer.customer_name = customer_name
		customer.customer_type = "Individual"

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
		supplier.supplier_type = "Individual"
		supplier.supplier_group = "All Supplier Groups"

		if currency:
			supplier.default_currency = currency
		supplier.save()
		return supplier.name
	else:
		return supplier_name


class TestAccountsController(IntegrationTestCase):
	"""
	Test Exchange Gain/Loss booking on various scenarios.
	Test Cases are numbered for better organization

	10 series - Sales Invoice against Payment Entries
	20 series - Sales Invoice against Journals
	30 series - Sales Invoice against Credit Notes
	40 series - Company default Cost center is unset
	50 series - Journals against Journals
	60 series - Journals against Payment Entries
	70 series - Advances in Separate party account. Both Party and Advance account are in Foreign currency.
	90 series - Dimension inheritence
	"""

	def setUp(self):
		self.create_company()
		self.create_account()
		self.create_item()
		self.create_parties()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def create_company(self):
		company_name = "_Test Company"
		self.company_abbr = abbr = "_TC"
		if frappe.db.exists("Company", company_name):
			company = frappe.get_doc("Company", company_name)
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": company_name,
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			)
			company = company.save()

		self.company = company.name
		self.cost_center = company.cost_center
		self.warehouse = "Stores - " + abbr
		self.finished_warehouse = "Finished Goods - " + abbr
		self.income_account = "Sales - " + abbr
		self.expense_account = "Cost of Goods Sold - " + abbr
		self.debit_to = "Debtors - " + abbr
		self.debit_usd = "Debtors USD - " + abbr
		self.cash = "Cash - " + abbr
		self.creditors = "Creditors - " + abbr

	def create_item(self):
		item = create_item(
			item_code="_Test Notebook", is_stock_item=0, company=self.company, warehouse=self.warehouse
		)
		self.item = item if isinstance(item, str) else item.item_code

	def create_parties(self):
		self.create_customer()
		self.create_supplier()

	def create_customer(self):
		self.customer = make_customer("_Test MC Customer USD", "USD")

	def create_supplier(self):
		self.supplier = make_supplier("_Test MC Supplier USD", "USD")

	def create_account(self):
		accounts = [
			frappe._dict(
				{
					"attribute_name": "debtors_usd",
					"name": "Debtors USD",
					"account_type": "Receivable",
					"account_currency": "USD",
					"parent_account": "Accounts Receivable - " + self.company_abbr,
				}
			),
			frappe._dict(
				{
					"attribute_name": "creditors_usd",
					"name": "Creditors USD",
					"account_type": "Payable",
					"account_currency": "USD",
					"parent_account": "Accounts Payable - " + self.company_abbr,
				}
			),
			# Advance accounts under Asset and Liability header
			frappe._dict(
				{
					"attribute_name": "advance_received_usd",
					"name": "Advance Received USD",
					"account_type": "Receivable",
					"account_currency": "USD",
					"parent_account": "Current Liabilities - " + self.company_abbr,
				}
			),
			frappe._dict(
				{
					"attribute_name": "advance_paid_usd",
					"name": "Advance Paid USD",
					"account_type": "Payable",
					"account_currency": "USD",
					"parent_account": "Current Assets - " + self.company_abbr,
				}
			),
		]

		for x in accounts:
			if not frappe.db.get_value("Account", filters={"account_name": x.name, "company": self.company}):
				acc = frappe.new_doc("Account")
				acc.account_name = x.name
				acc.parent_account = x.parent_account
				acc.company = self.company
				acc.account_currency = x.account_currency
				acc.account_type = x.account_type
				acc.insert()
			else:
				name = frappe.db.get_value(
					"Account",
					filters={"account_name": x.name, "company": self.company},
					fieldname="name",
					pluck=True,
				)
				acc = frappe.get_doc("Account", name)
			setattr(self, x.attribute_name, acc.name)

	def setup_advance_accounts_in_party_master(self):
		company = frappe.get_doc("Company", self.company)
		company.book_advance_payments_in_separate_party_account = 1
		company.save()

		customer = frappe.get_doc("Customer", self.customer)
		customer.append(
			"accounts",
			{
				"company": self.company,
				"account": self.debtors_usd,
				"advance_account": self.advance_received_usd,
			},
		)
		customer.save()

		supplier = frappe.get_doc("Supplier", self.supplier)
		supplier.append(
			"accounts",
			{
				"company": self.company,
				"account": self.creditors_usd,
				"advance_account": self.advance_paid_usd,
			},
		)
		supplier.save()

	def remove_advance_accounts_from_party_master(self):
		company = frappe.get_doc("Company", self.company)
		company.book_advance_payments_in_separate_party_account = 0
		company.save()
		customer = frappe.get_doc("Customer", self.customer)
		customer.accounts = []
		customer.save()
		supplier = frappe.get_doc("Supplier", self.supplier)
		supplier.accounts = []
		supplier.save()

	def create_sales_invoice(
		self,
		qty=1,
		rate=1,
		conversion_rate=80,
		posting_date=None,
		do_not_save=False,
		do_not_submit=False,
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
			debit_to=self.debit_usd,
			parent_cost_center=self.cost_center,
			update_stock=0,
			currency="USD",
			conversion_rate=conversion_rate,
			is_pos=0,
			is_return=0,
			return_against=None,
			income_account=self.income_account,
			expense_account=self.expense_account,
			do_not_save=do_not_save,
			do_not_submit=do_not_submit,
		)
		return sinv

	def create_payment_entry(
		self, amount=1, source_exc_rate=75, posting_date=None, customer=None, submit=True
	):
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
			paid_from=self.debit_usd,
			paid_to=self.cash,
			paid_amount=amount,
		)
		payment.source_exchange_rate = source_exc_rate
		payment.received_amount = source_exc_rate * amount
		payment.posting_date = posting_date
		return payment

	def create_purchase_invoice(
		self,
		qty=1,
		rate=1,
		conversion_rate=80,
		posting_date=None,
		do_not_save=False,
		do_not_submit=False,
	):
		"""
		Helper function to populate default values in purchase invoice
		"""
		if posting_date is None:
			posting_date = nowdate()

		pinv = make_purchase_invoice(
			posting_date=posting_date,
			qty=qty,
			rate=rate,
			company=self.company,
			supplier=self.supplier,
			item_code=self.item,
			item_name=self.item,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			parent_cost_center=self.cost_center,
			update_stock=0,
			currency="USD",
			conversion_rate=conversion_rate,
			is_pos=0,
			is_return=0,
			income_account=self.income_account,
			expense_account=self.expense_account,
			do_not_save=True,
		)
		pinv.credit_to = self.creditors_usd
		if not do_not_save:
			pinv.save()
			if not do_not_submit:
				pinv.submit()
		return pinv

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
		self,
		acc1=None,
		acc1_exc_rate=None,
		acc2_exc_rate=None,
		acc2=None,
		acc1_amount=0,
		acc2_amount=0,
		posting_date=None,
		cost_center=None,
	):
		je = frappe.new_doc("Journal Entry")
		je.posting_date = posting_date or nowdate()
		je.company = self.company
		je.user_remark = "test"
		je.multi_currency = True
		if not cost_center:
			cost_center = self.cost_center
		je.set(
			"accounts",
			[
				{
					"account": acc1,
					"exchange_rate": acc1_exc_rate or 1,
					"cost_center": cost_center,
					"debit_in_account_currency": acc1_amount if acc1_amount > 0 else 0,
					"credit_in_account_currency": abs(acc1_amount) if acc1_amount < 0 else 0,
					"debit": acc1_amount * acc1_exc_rate if acc1_amount > 0 else 0,
					"credit": abs(acc1_amount * acc1_exc_rate) if acc1_amount < 0 else 0,
				},
				{
					"account": acc2,
					"exchange_rate": acc2_exc_rate or 1,
					"cost_center": cost_center,
					"credit_in_account_currency": acc2_amount if acc2_amount > 0 else 0,
					"debit_in_account_currency": abs(acc2_amount) if acc2_amount < 0 else 0,
					"credit": acc2_amount * acc2_exc_rate if acc2_amount > 0 else 0,
					"debit": abs(acc2_amount * acc2_exc_rate) if acc2_amount < 0 else 0,
				},
			],
		)
		return je

	def get_journals_for(self, voucher_type: str, voucher_no: str) -> list:
		journals = []
		if voucher_type and voucher_no:
			journals = frappe.db.get_all(
				"Journal Entry Account",
				filters={"reference_type": voucher_type, "reference_name": voucher_no, "docstatus": 1},
				fields=["parent"],
			)
		return journals

	def assert_ledger_outstanding(
		self,
		voucher_type: str,
		voucher_no: str,
		outstanding: float,
		outstanding_in_account_currency: float,
	) -> None:
		"""
		Assert outstanding amount based on ledger on both company/base currency and account currency
		"""

		ple = qb.DocType("Payment Ledger Entry")
		current_outstanding = (
			qb.from_(ple)
			.select(
				Sum(ple.amount).as_("outstanding"),
				Sum(ple.amount_in_account_currency).as_("outstanding_in_account_currency"),
			)
			.where(
				(ple.against_voucher_type == voucher_type)
				& (ple.against_voucher_no == voucher_no)
				& (ple.delinked == 0)
			)
			.run(as_dict=True)[0]
		)
		self.assertEqual(outstanding, current_outstanding.outstanding)
		self.assertEqual(outstanding_in_account_currency, current_outstanding.outstanding_in_account_currency)

	def test_10_payment_against_sales_invoice(self):
		# Sales Invoice in Foreign Currency
		rate = 80
		rate_in_account_currency = 1

		si = self.create_sales_invoice(qty=1, rate=rate_in_account_currency)

		# Test payments with different exchange rates
		for exc_rate in [75.9, 83.1, 80.01]:
			with self.subTest(exc_rate=exc_rate):
				pe = self.create_payment_entry(amount=1, source_exc_rate=exc_rate).save()
				pe.append(
					"references",
					{"reference_doctype": si.doctype, "reference_name": si.name, "allocated_amount": 1},
				)
				pe = pe.save().submit()

				# Outstanding in both currencies should be '0'
				si.reload()
				self.assertEqual(si.outstanding_amount, 0)
				self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

				# Exchange Gain/Loss Journal should've been created.
				exc_je_for_si = self.get_journals_for(si.doctype, si.name)
				exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
				self.assertNotEqual(exc_je_for_si, [])
				self.assertEqual(len(exc_je_for_si), 1)
				self.assertEqual(len(exc_je_for_pe), 1)
				self.assertEqual(exc_je_for_si[0], exc_je_for_pe[0])

				# Cancel Payment
				pe.cancel()

				# outstanding should be same as grand total
				si.reload()
				self.assertEqual(si.outstanding_amount, rate_in_account_currency)
				self.assert_ledger_outstanding(si.doctype, si.name, rate, rate_in_account_currency)

				# Exchange Gain/Loss Journal should've been cancelled
				exc_je_for_si = self.get_journals_for(si.doctype, si.name)
				exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
				self.assertEqual(exc_je_for_si, [])
				self.assertEqual(exc_je_for_pe, [])

	def test_11_advance_against_sales_invoice(self):
		# Advance Payment
		adv = self.create_payment_entry(amount=1, source_exc_rate=85).save().submit()
		adv.reload()

		# Sales Invoices in different exchange rates
		for exc_rate in [75.9, 83.1, 80.01]:
			with self.subTest(exc_rate=exc_rate):
				si = self.create_sales_invoice(qty=1, conversion_rate=exc_rate, rate=1, do_not_submit=True)
				advances = si.get_advance_entries()
				self.assertEqual(len(advances), 1)
				self.assertEqual(advances[0].reference_name, adv.name)
				si.append(
					"advances",
					{
						"doctype": "Sales Invoice Advance",
						"reference_type": advances[0].reference_type,
						"reference_name": advances[0].reference_name,
						"reference_row": advances[0].reference_row,
						"advance_amount": 1,
						"allocated_amount": 1,
						"ref_exchange_rate": advances[0].exchange_rate,
						"remarks": advances[0].remarks,
					},
				)

				si = si.save()
				si = si.submit()

				# Outstanding in both currencies should be '0'
				adv.reload()
				self.assertEqual(si.outstanding_amount, 0)
				self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

				# Exchange Gain/Loss Journal should've been created.
				exc_je_for_si = self.get_journals_for(si.doctype, si.name)
				exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
				self.assertNotEqual(exc_je_for_si, [])
				self.assertEqual(len(exc_je_for_si), 1)
				self.assertEqual(len(exc_je_for_adv), 1)
				self.assertEqual(exc_je_for_si, exc_je_for_adv)

				# Cancel Invoice
				si.cancel()

				# Exchange Gain/Loss Journal should've been cancelled
				exc_je_for_si = self.get_journals_for(si.doctype, si.name)
				exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
				self.assertEqual(exc_je_for_si, [])
				self.assertEqual(exc_je_for_adv, [])

	def test_12_partial_advance_and_payment_for_sales_invoice(self):
		"""
		Sales invoice with partial advance payment, and a normal payment reconciled
		"""
		# Partial Advance
		adv = self.create_payment_entry(amount=1, source_exc_rate=85).save().submit()
		adv.reload()

		# sales invoice with advance(partial amount)
		rate_in_account_currency = 1
		si = self.create_sales_invoice(
			qty=2, conversion_rate=80, rate=rate_in_account_currency, do_not_submit=True
		)
		advances = si.get_advance_entries()
		self.assertEqual(len(advances), 1)
		self.assertEqual(advances[0].reference_name, adv.name)
		si.append(
			"advances",
			{
				"doctype": "Sales Invoice Advance",
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": 1,
				"allocated_amount": 1,
				"ref_exchange_rate": advances[0].exchange_rate,
				"remarks": advances[0].remarks,
			},
		)
		si = si.save()
		si = si.submit()

		# Outstanding should be there in both currencies
		si.reload()
		self.assertEqual(si.outstanding_amount, 1)  # account currency
		self.assert_ledger_outstanding(si.doctype, si.name, 80.0, 1.0)

		# Exchange Gain/Loss Journal should've been created for the partial advance
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_adv), 1)
		self.assertEqual(exc_je_for_si, exc_je_for_adv)

		# Payment for remaining amount
		pe = self.create_payment_entry(amount=1, source_exc_rate=75).save()
		pe.append(
			"references",
			{"reference_doctype": si.doctype, "reference_name": si.name, "allocated_amount": 1},
		)
		pe = pe.save().submit()

		# Outstanding in both currencies should be '0'
		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

		# Exchange Gain/Loss Journal should've been created for the payment
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		self.assertNotEqual(exc_je_for_si, [])
		# There should be 2 JE's now. One for the advance and one for the payment
		self.assertEqual(len(exc_je_for_si), 2)
		self.assertEqual(len(exc_je_for_pe), 1)
		self.assertEqual(exc_je_for_si, exc_je_for_pe + exc_je_for_adv)

		# Cancel Invoice
		si.reload()
		si.cancel()

		# Exchange Gain/Loss Journal should been cancelled
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		self.assertEqual(exc_je_for_si, [])
		self.assertEqual(exc_je_for_pe, [])
		self.assertEqual(exc_je_for_adv, [])

	def test_13_partial_advance_and_payment_for_invoice_with_cancellation(self):
		"""
		Invoice with partial advance payment, and a normal payment. Then cancel advance and payment.
		"""
		# Partial Advance
		adv = self.create_payment_entry(amount=1, source_exc_rate=85).save().submit()
		adv.reload()

		# invoice with advance(partial amount)
		si = self.create_sales_invoice(qty=2, conversion_rate=80, rate=1, do_not_submit=True)
		advances = si.get_advance_entries()
		self.assertEqual(len(advances), 1)
		self.assertEqual(advances[0].reference_name, adv.name)
		si.append(
			"advances",
			{
				"doctype": "Sales Invoice Advance",
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"advance_amount": 1,
				"allocated_amount": 1,
				"ref_exchange_rate": advances[0].exchange_rate,
				"remarks": advances[0].remarks,
			},
		)
		si = si.save()
		si = si.submit()

		# Outstanding should be there in both currencies
		si.reload()
		self.assertEqual(si.outstanding_amount, 1)  # account currency
		self.assert_ledger_outstanding(si.doctype, si.name, 80.0, 1.0)

		# Exchange Gain/Loss Journal should've been created for the partial advance
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_adv), 1)
		self.assertEqual(exc_je_for_si, exc_je_for_adv)

		# Payment(remaining amount)
		pe = self.create_payment_entry(amount=1, source_exc_rate=75).save()
		pe.append(
			"references",
			{"reference_doctype": si.doctype, "reference_name": si.name, "allocated_amount": 1},
		)
		pe = pe.save().submit()

		# Outstanding should be '0' in both currencies
		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

		# Exchange Gain/Loss Journal should've been created for the payment
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		self.assertNotEqual(exc_je_for_si, [])
		# There should be 2 JE's now. One for the advance and one for the payment
		self.assertEqual(len(exc_je_for_si), 2)
		self.assertEqual(len(exc_je_for_pe), 1)
		self.assertEqual(exc_je_for_si, exc_je_for_pe + exc_je_for_adv)

		adv.reload()
		adv.cancel()

		# Outstanding should be there in both currencies, since advance is cancelled.
		si.reload()
		self.assertEqual(si.outstanding_amount, 1)  # account currency
		self.assert_ledger_outstanding(si.doctype, si.name, 80.0, 1.0)

		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		# Exchange Gain/Loss Journal for advance should been cancelled
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_pe), 1)
		self.assertEqual(exc_je_for_adv, [])

	def test_14_same_payment_split_against_invoice(self):
		# Invoice in Foreign Currency
		si = self.create_sales_invoice(qty=2, conversion_rate=80, rate=1)
		# Payment
		pe = self.create_payment_entry(amount=2, source_exc_rate=75).save()
		pe.append(
			"references",
			{"reference_doctype": si.doctype, "reference_name": si.name, "allocated_amount": 1},
		)
		pe = pe.save().submit()

		# There should be outstanding in both currencies
		si.reload()
		self.assertEqual(si.outstanding_amount, 1)
		self.assert_ledger_outstanding(si.doctype, si.name, 80.0, 1.0)

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_pe), 1)
		self.assertEqual(exc_je_for_si[0], exc_je_for_pe[0])

		# Reconcile the remaining amount
		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = self.company
		pr.party_type = "Customer"
		pr.party = self.customer
		pr.receivable_payable_account = self.debit_usd
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# Exc gain/loss journal should have been creaetd for the reconciled amount
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		self.assertEqual(len(exc_je_for_si), 2)
		self.assertEqual(len(exc_je_for_pe), 2)
		self.assertEqual(exc_je_for_si, exc_je_for_pe)

		# There should be no outstanding
		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

		# Cancel Payment
		pe.reload()
		pe.cancel()

		si.reload()
		self.assertEqual(si.outstanding_amount, 2)
		self.assert_ledger_outstanding(si.doctype, si.name, 160.0, 2.0)

		# Exchange Gain/Loss Journal should've been cancelled
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		self.assertEqual(exc_je_for_si, [])
		self.assertEqual(exc_je_for_pe, [])

	def test_15_gain_loss_on_different_posting_date(self):
		# Invoice in Foreign Currency
		si = self.create_sales_invoice(
			posting_date=add_days(nowdate(), -2), qty=2, conversion_rate=80, rate=1
		)
		# Payment
		pe = (
			self.create_payment_entry(posting_date=add_days(nowdate(), -1), amount=2, source_exc_rate=75)
			.save()
			.submit()
		)

		# There should be outstanding in both currencies
		si.reload()
		self.assertEqual(si.outstanding_amount, 2)
		self.assert_ledger_outstanding(si.doctype, si.name, 160.0, 2.0)

		# Reconcile the remaining amount
		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = self.company
		pr.party_type = "Customer"
		pr.party = self.customer
		pr.receivable_payable_account = self.debit_usd
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.allocation[0].gain_loss_posting_date = add_days(nowdate(), 1)
		pr.reconcile()

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_pe), 1)
		self.assertEqual(exc_je_for_si[0], exc_je_for_pe[0])

		self.assertEqual(
			frappe.db.get_value("Journal Entry", exc_je_for_si[0].parent, "posting_date"),
			getdate(add_days(nowdate(), 1)),
		)

		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# There should be no outstanding
		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

		# Cancel Payment
		pe.reload()
		pe.cancel()

		si.reload()
		self.assertEqual(si.outstanding_amount, 2)
		self.assert_ledger_outstanding(si.doctype, si.name, 160.0, 2.0)

		# Exchange Gain/Loss Journal should've been cancelled
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		self.assertEqual(exc_je_for_si, [])
		self.assertEqual(exc_je_for_pe, [])

	@IntegrationTestCase.change_settings(
		"Stock Settings", {"allow_internal_transfer_at_arms_length_price": 1}
	)
	def test_16_internal_transfer_at_arms_length_price(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_purchase_invoice
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		prepare_data_for_internal_transfer()
		company = "_Test Company with perpetual inventory"
		target_warehouse = create_warehouse("_Test Internal Warehouse New 1", company=company)
		warehouse = create_warehouse("_Test Internal Warehouse New 2", company=company)
		arms_length_price = 40

		si = create_sales_invoice(
			company=company,
			customer="_Test Internal Customer 2",
			debit_to="Debtors - TCP1",
			target_warehouse=target_warehouse,
			warehouse=warehouse,
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
			update_stock=True,
			do_not_save=True,
			do_not_submit=True,
		)

		si.items[0].rate = arms_length_price
		si.save()
		# rate should not reset to incoming rate
		self.assertEqual(si.items[0].rate, arms_length_price)

		frappe.db.set_single_value("Stock Settings", "allow_internal_transfer_at_arms_length_price", 0)
		si.items[0].rate = arms_length_price
		si.save()
		# rate should reset to incoming rate
		self.assertEqual(si.items[0].rate, 100)

		si.update_stock = 0
		si.save()
		si.submit()

		pi = make_inter_company_purchase_invoice(si.name)
		pi.update_stock = 1
		pi.items[0].rate = arms_length_price
		pi.items[0].warehouse = target_warehouse
		pi.items[0].from_warehouse = warehouse
		pi.save()

		self.assertEqual(pi.items[0].rate, 100)
		self.assertEqual(pi.items[0].valuation_rate, 100)

		frappe.db.set_single_value("Stock Settings", "allow_internal_transfer_at_arms_length_price", 1)
		pi = make_inter_company_purchase_invoice(si.name)
		pi.update_stock = 1
		pi.items[0].rate = arms_length_price
		pi.items[0].warehouse = target_warehouse
		pi.items[0].from_warehouse = warehouse
		pi.save()

		self.assertEqual(pi.items[0].rate, arms_length_price)
		self.assertEqual(pi.items[0].valuation_rate, 100)

	@IntegrationTestCase.change_settings(
		"Accounts Settings", {"exchange_gain_loss_posting_date": "Reconciliation Date"}
	)
	def test_17_gain_loss_posting_date_for_normal_payment(self):
		# Sales Invoice in Foreign Currency
		rate = 80
		rate_in_account_currency = 1

		adv_date = convert_to_date(add_days(nowdate(), -2))
		inv_date = convert_to_date(add_days(nowdate(), -1))

		si = self.create_sales_invoice(posting_date=inv_date, qty=1, rate=rate_in_account_currency)

		# Test payments with different exchange rates
		pe = self.create_payment_entry(posting_date=adv_date, amount=1, source_exc_rate=75.1).save().submit()

		pr = self.create_payment_reconciliation()
		pr.from_invoice_date = add_days(nowdate(), -1)
		pr.to_invoice_date = nowdate()
		pr.from_payment_date = add_days(nowdate(), -2)
		pr.to_payment_date = nowdate()

		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# Outstanding in both currencies should be '0'
		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_pe), 1)
		self.assertEqual(exc_je_for_si[0], exc_je_for_pe[0])

		self.assertEqual(
			getdate(nowdate()), frappe.db.get_value("Journal Entry", exc_je_for_pe[0].parent, "posting_date")
		)
		# Cancel Payment
		pe.reload()
		pe.cancel()

		# outstanding should be same as grand total
		si.reload()
		self.assertEqual(si.outstanding_amount, rate_in_account_currency)
		self.assert_ledger_outstanding(si.doctype, si.name, rate, rate_in_account_currency)

		# Exchange Gain/Loss Journal should've been cancelled
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		self.assertEqual(exc_je_for_si, [])
		self.assertEqual(exc_je_for_pe, [])

	@IntegrationTestCase.change_settings(
		"Accounts Settings",
		{"add_taxes_from_item_tax_template": 0, "add_taxes_from_taxes_and_charges_template": 1},
	)
	def test_18_fetch_taxes_based_on_taxes_and_charges_template(self):
		# Create a Sales Taxes and Charges Template
		if not frappe.db.exists("Sales Taxes and Charges Template", "_Test Tax - _TC"):
			doc = frappe.new_doc("Sales Taxes and Charges Template")
			doc.company = self.company
			doc.title = "_Test Tax"
			doc.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": "Sales Expenses - _TC",
					"description": "Test taxes",
					"rate": 9,
				},
			)
			doc.insert()

		# Create a Sales Invoice
		sinv = frappe.new_doc("Sales Invoice")
		sinv.customer = self.customer
		sinv.company = self.company
		sinv.currency = "INR"
		sinv.taxes_and_charges = "_Test Tax - _TC"
		sinv.append("items", {"item_code": "_Test Item", "qty": 1, "rate": 50})
		sinv.insert()

		self.assertEqual(sinv.total_taxes_and_charges, 4.5)

	@IntegrationTestCase.change_settings(
		"Accounts Settings",
		{"add_taxes_from_item_tax_template": 1, "add_taxes_from_taxes_and_charges_template": 0},
	)
	def test_19_fetch_taxes_based_on_item_tax_template_template(self):
		# Create a Sales Invoice
		sinv = frappe.new_doc("Sales Invoice")
		sinv.customer = self.customer
		sinv.company = self.company
		sinv.currency = "INR"
		sinv.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"rate": 50,
				"item_tax_template": "_Test Account Excise Duty @ 10 - _TC",
			},
		)
		sinv.insert()

		self.assertEqual(sinv.taxes[0].account_head, "_Test Account Excise Duty - _TC")
		self.assertEqual(sinv.total_taxes_and_charges, 5)

	def test_20_journal_against_sales_invoice(self):
		# Invoice in Foreign Currency
		si = self.create_sales_invoice(qty=1, conversion_rate=80, rate=1)
		# Payment
		je = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=75,
			acc2=self.cash,
			acc1_amount=-1,
			acc2_amount=-75,
			acc2_exc_rate=1,
		)
		je.accounts[0].party_type = "Customer"
		je.accounts[0].party = self.customer
		je = je.save().submit()

		# Reconcile the remaining amount
		pr = self.create_payment_reconciliation()
		# pr.receivable_payable_account = self.debit_usd
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# There should be no outstanding in both currencies
		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_je = self.get_journals_for(je.doctype, je.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(
			len(exc_je_for_si), 2
		)  # payment also has reference. so, there are 2 journals referencing invoice
		self.assertEqual(len(exc_je_for_je), 1)
		self.assertIn(exc_je_for_je[0], exc_je_for_si)

		# Cancel Payment
		je.reload()
		je.cancel()

		si.reload()
		self.assertEqual(si.outstanding_amount, 1)
		self.assert_ledger_outstanding(si.doctype, si.name, 80.0, 1.0)

		# Exchange Gain/Loss Journal should've been cancelled
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_je = self.get_journals_for(je.doctype, je.name)
		self.assertEqual(exc_je_for_si, [])
		self.assertEqual(exc_je_for_je, [])

	def test_21_advance_journal_against_sales_invoice(self):
		# Advance Payment
		adv_exc_rate = 80
		adv = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=adv_exc_rate,
			acc2=self.cash,
			acc1_amount=-1,
			acc2_amount=adv_exc_rate * -1,
			acc2_exc_rate=1,
		)
		adv.accounts[0].party_type = "Customer"
		adv.accounts[0].party = self.customer
		adv.accounts[0].is_advance = "Yes"
		adv = adv.save().submit()
		adv.reload()

		# Sales Invoices in different exchange rates
		for exc_rate in [75.9, 83.1]:
			with self.subTest(exc_rate=exc_rate):
				si = self.create_sales_invoice(qty=1, conversion_rate=exc_rate, rate=1, do_not_submit=True)
				advances = si.get_advance_entries()
				self.assertEqual(len(advances), 1)
				self.assertEqual(advances[0].reference_name, adv.name)
				si.append(
					"advances",
					{
						"doctype": "Sales Invoice Advance",
						"reference_type": advances[0].reference_type,
						"reference_name": advances[0].reference_name,
						"reference_row": advances[0].reference_row,
						"advance_amount": 1,
						"allocated_amount": 1,
						"ref_exchange_rate": advances[0].exchange_rate,
						"remarks": advances[0].remarks,
					},
				)

				si = si.save()
				si = si.submit()

				# Outstanding in both currencies should be '0'
				adv.reload()
				self.assertEqual(si.outstanding_amount, 0)
				self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

				# Exchange Gain/Loss Journal should've been created.
				exc_je_for_si = [
					x for x in self.get_journals_for(si.doctype, si.name) if x.parent != adv.name
				]
				exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
				self.assertNotEqual(exc_je_for_si, [])
				self.assertEqual(len(exc_je_for_si), 1)
				self.assertEqual(len(exc_je_for_adv), 1)
				self.assertEqual(exc_je_for_si, exc_je_for_adv)

				# Cancel Invoice
				si.cancel()

				# Exchange Gain/Loss Journal should've been cancelled
				exc_je_for_si = self.get_journals_for(si.doctype, si.name)
				exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
				self.assertEqual(exc_je_for_si, [])
				self.assertEqual(exc_je_for_adv, [])

	def test_22_partial_advance_and_payment_for_invoice_with_cancellation(self):
		"""
		Invoice with partial advance payment as Journal, and a normal payment. Then cancel advance and payment.
		"""
		# Partial Advance
		adv_exc_rate = 75
		adv = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=adv_exc_rate,
			acc2=self.cash,
			acc1_amount=-1,
			acc2_amount=adv_exc_rate * -1,
			acc2_exc_rate=1,
		)
		adv.accounts[0].party_type = "Customer"
		adv.accounts[0].party = self.customer
		adv.accounts[0].is_advance = "Yes"
		adv = adv.save().submit()
		adv.reload()

		# invoice with advance(partial amount)
		si = self.create_sales_invoice(qty=3, conversion_rate=80, rate=1, do_not_submit=True)
		advances = si.get_advance_entries()
		self.assertEqual(len(advances), 1)
		self.assertEqual(advances[0].reference_name, adv.name)
		si.append(
			"advances",
			{
				"doctype": "Sales Invoice Advance",
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"reference_row": advances[0].reference_row,
				"advance_amount": 1,
				"allocated_amount": 1,
				"ref_exchange_rate": advances[0].exchange_rate,
				"remarks": advances[0].remarks,
			},
		)

		si = si.save()
		si = si.submit()

		# Outstanding should be there in both currencies
		si.reload()
		self.assertEqual(si.outstanding_amount, 2)  # account currency
		self.assert_ledger_outstanding(si.doctype, si.name, 160.0, 2.0)

		# Exchange Gain/Loss Journal should've been created for the partial advance
		exc_je_for_si = [x for x in self.get_journals_for(si.doctype, si.name) if x.parent != adv.name]
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_adv), 1)
		self.assertEqual(exc_je_for_si, exc_je_for_adv)

		# Payment
		adv2_exc_rate = 83
		pay = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=adv2_exc_rate,
			acc2=self.cash,
			acc1_amount=-2,
			acc2_amount=adv2_exc_rate * -2,
			acc2_exc_rate=1,
		)
		pay.accounts[0].party_type = "Customer"
		pay.accounts[0].party = self.customer
		pay.accounts[0].is_advance = "Yes"
		pay = pay.save().submit()
		pay.reload()

		# Reconcile the remaining amount
		pr = self.create_payment_reconciliation()
		# pr.receivable_payable_account = self.debit_usd
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# Outstanding should be '0' in both currencies
		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

		# Exchange Gain/Loss Journal should've been created for the payment
		exc_je_for_si = [
			x
			for x in self.get_journals_for(si.doctype, si.name)
			if x.parent != adv.name and x.parent != pay.name
		]
		exc_je_for_pe = self.get_journals_for(pay.doctype, pay.name)
		self.assertNotEqual(exc_je_for_si, [])
		# There should be 2 JE's now. One for the advance and one for the payment
		self.assertEqual(len(exc_je_for_si), 2)
		self.assertEqual(len(exc_je_for_pe), 1)
		self.assertEqual(exc_je_for_si, exc_je_for_pe + exc_je_for_adv)

		adv.reload()
		adv.cancel()

		# Outstanding should be there in both currencies, since advance is cancelled.
		si.reload()
		self.assertEqual(si.outstanding_amount, 1)  # account currency
		self.assert_ledger_outstanding(si.doctype, si.name, 80.0, 1.0)

		exc_je_for_si = [
			x
			for x in self.get_journals_for(si.doctype, si.name)
			if x.parent != adv.name and x.parent != pay.name
		]
		exc_je_for_pe = self.get_journals_for(pay.doctype, pay.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		# Exchange Gain/Loss Journal for advance should been cancelled
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_pe), 1)
		self.assertEqual(exc_je_for_adv, [])

	def test_23_same_journal_split_against_single_invoice(self):
		# Invoice in Foreign Currency
		si = self.create_sales_invoice(qty=2, conversion_rate=80, rate=1)
		# Payment
		je = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=75,
			acc2=self.cash,
			acc1_amount=-2,
			acc2_amount=-150,
			acc2_exc_rate=1,
		)
		je.accounts[0].party_type = "Customer"
		je.accounts[0].party = self.customer
		je = je.save().submit()

		# Reconcile the first half
		pr = self.create_payment_reconciliation()
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		difference_amount = pr.calculate_difference_on_allocation_change(
			[x.as_dict() for x in pr.payments], [x.as_dict() for x in pr.invoices], 1
		)
		pr.allocation[0].allocated_amount = 1
		pr.allocation[0].difference_amount = difference_amount
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)

		# There should be outstanding in both currencies
		si.reload()
		self.assertEqual(si.outstanding_amount, 1)
		self.assert_ledger_outstanding(si.doctype, si.name, 80.0, 1.0)

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = [x for x in self.get_journals_for(si.doctype, si.name) if x.parent != je.name]
		exc_je_for_je = self.get_journals_for(je.doctype, je.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_je), 1)
		self.assertIn(exc_je_for_je[0], exc_je_for_si)

		# reconcile remaining half
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.allocation[0].allocated_amount = 1
		pr.allocation[0].difference_amount = difference_amount
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = [x for x in self.get_journals_for(si.doctype, si.name) if x.parent != je.name]
		exc_je_for_je = self.get_journals_for(je.doctype, je.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 2)
		self.assertEqual(len(exc_je_for_je), 2)
		self.assertIn(exc_je_for_je[0], exc_je_for_si)

		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

		# Cancel Payment
		je.reload()
		je.cancel()

		si.reload()
		self.assertEqual(si.outstanding_amount, 2)
		self.assert_ledger_outstanding(si.doctype, si.name, 160.0, 2.0)

		# Exchange Gain/Loss Journal should've been cancelled
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_je = self.get_journals_for(je.doctype, je.name)
		self.assertEqual(exc_je_for_si, [])
		self.assertEqual(exc_je_for_je, [])

	def test_24_journal_against_multiple_invoices(self):
		si1 = self.create_sales_invoice(qty=1, conversion_rate=80, rate=1)
		si2 = self.create_sales_invoice(qty=1, conversion_rate=80, rate=1)

		# Payment
		je = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=75,
			acc2=self.cash,
			acc1_amount=-2,
			acc2_amount=-150,
			acc2_exc_rate=1,
		)
		je.accounts[0].party_type = "Customer"
		je.accounts[0].party = self.customer
		je = je.save().submit()

		pr = self.create_payment_reconciliation()
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 2)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		si1.reload()
		si2.reload()

		self.assertEqual(si1.outstanding_amount, 0)
		self.assertEqual(si2.outstanding_amount, 0)
		self.assert_ledger_outstanding(si1.doctype, si1.name, 0.0, 0.0)
		self.assert_ledger_outstanding(si2.doctype, si2.name, 0.0, 0.0)

		# Exchange Gain/Loss Journal should've been created
		# remove payment JE from list
		exc_je_for_si1 = [x for x in self.get_journals_for(si1.doctype, si1.name) if x.parent != je.name]
		exc_je_for_si2 = [x for x in self.get_journals_for(si2.doctype, si2.name) if x.parent != je.name]
		exc_je_for_je = [x for x in self.get_journals_for(je.doctype, je.name) if x.parent != je.name]
		self.assertEqual(len(exc_je_for_si1), 1)
		self.assertEqual(len(exc_je_for_si2), 1)
		self.assertEqual(len(exc_je_for_je), 2)

		si1.cancel()
		# Gain/Loss JE of si1 should've been cancelled
		exc_je_for_si1 = [x for x in self.get_journals_for(si1.doctype, si1.name) if x.parent != je.name]
		exc_je_for_si2 = [x for x in self.get_journals_for(si2.doctype, si2.name) if x.parent != je.name]
		exc_je_for_je = [x for x in self.get_journals_for(je.doctype, je.name) if x.parent != je.name]
		self.assertEqual(len(exc_je_for_si1), 0)
		self.assertEqual(len(exc_je_for_si2), 1)
		self.assertEqual(len(exc_je_for_je), 1)

	def test_30_cr_note_against_sales_invoice(self):
		"""
		Reconciling Cr Note against Sales Invoice, both having different exchange rates
		"""
		# Invoice in Foreign currency
		si = self.create_sales_invoice(qty=2, conversion_rate=80, rate=1)

		# Cr Note in Foreign currency of different exchange rate
		cr_note = self.create_sales_invoice(qty=-2, conversion_rate=75, rate=1, do_not_save=True)
		cr_note.is_return = 1
		cr_note.save().submit()

		# Reconcile the first half
		pr = self.create_payment_reconciliation()
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		difference_amount = pr.calculate_difference_on_allocation_change(
			[x.as_dict() for x in pr.payments], [x.as_dict() for x in pr.invoices], 1
		)
		pr.allocation[0].allocated_amount = 1
		pr.allocation[0].difference_amount = difference_amount
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_cr = self.get_journals_for(cr_note.doctype, cr_note.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 2)
		self.assertEqual(len(exc_je_for_cr), 2)
		self.assertEqual(exc_je_for_cr, exc_je_for_si)

		si.reload()
		self.assertEqual(si.outstanding_amount, 1)
		self.assert_ledger_outstanding(si.doctype, si.name, 80.0, 1.0)

		cr_note.reload()
		cr_note.cancel()

		# with the introduction of 'cancel_system_generated_credit_debit_notes' in accounts controller
		# JE(Credit Note) will be cancelled once the parent is cancelled
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_cr = self.get_journals_for(cr_note.doctype, cr_note.name)
		self.assertEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 0)
		self.assertEqual(len(exc_je_for_cr), 0)

		# No references, full outstanding
		si.reload()
		self.assertEqual(si.outstanding_amount, 2)
		self.assert_ledger_outstanding(si.doctype, si.name, 160.0, 2.0)

	def test_40_cost_center_from_payment_entry(self):
		"""
		Gain/Loss JE should inherit cost center from payment if company default is unset
		"""
		# remove default cost center
		cc = frappe.db.get_value("Company", self.company, "cost_center")
		frappe.db.set_value("Company", self.company, "cost_center", None)

		rate_in_account_currency = 1
		si = self.create_sales_invoice(qty=1, rate=rate_in_account_currency, do_not_submit=True)
		si.cost_center = None
		si.save().submit()

		pe = get_payment_entry(si.doctype, si.name)
		pe.source_exchange_rate = 75
		pe.received_amount = 75
		pe.cost_center = self.cost_center
		pe = pe.save().submit()

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_pe = self.get_journals_for(pe.doctype, pe.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_pe), 1)
		self.assertEqual(exc_je_for_si[0], exc_je_for_pe[0])

		self.assertEqual(
			[self.cost_center, self.cost_center],
			frappe.db.get_all(
				"Journal Entry Account", filters={"parent": exc_je_for_si[0].parent}, pluck="cost_center"
			),
		)
		frappe.db.set_value("Company", self.company, "cost_center", cc)

	def test_41_cost_center_from_journal_entry(self):
		"""
		Gain/Loss JE should inherit cost center from payment if company default is unset
		"""
		# remove default cost center
		cc = frappe.db.get_value("Company", self.company, "cost_center")
		frappe.db.set_value("Company", self.company, "cost_center", None)

		rate_in_account_currency = 1
		si = self.create_sales_invoice(qty=1, rate=rate_in_account_currency, do_not_submit=True)
		si.cost_center = None
		si.save().submit()

		je = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=75,
			acc2=self.cash,
			acc1_amount=-1,
			acc2_amount=-75,
			acc2_exc_rate=1,
		)
		je.accounts[0].party_type = "Customer"
		je.accounts[0].party = self.customer
		je.accounts[0].cost_center = self.cost_center
		je = je.save().submit()

		# Reconcile
		pr = self.create_payment_reconciliation()
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = [x for x in self.get_journals_for(si.doctype, si.name) if x.parent != je.name]
		exc_je_for_je = [x for x in self.get_journals_for(je.doctype, je.name) if x.parent != je.name]
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_je), 1)
		self.assertEqual(exc_je_for_si[0], exc_je_for_je[0])

		self.assertEqual(
			[self.cost_center, self.cost_center],
			frappe.db.get_all(
				"Journal Entry Account", filters={"parent": exc_je_for_si[0].parent}, pluck="cost_center"
			),
		)
		frappe.db.set_value("Company", self.company, "cost_center", cc)

	def test_42_cost_center_from_cr_note(self):
		"""
		Gain/Loss JE should inherit cost center from payment if company default is unset
		"""
		# remove default cost center
		cc = frappe.db.get_value("Company", self.company, "cost_center")
		frappe.db.set_value("Company", self.company, "cost_center", None)

		rate_in_account_currency = 1
		si = self.create_sales_invoice(qty=1, rate=rate_in_account_currency, do_not_submit=True)
		si.cost_center = None
		si.save().submit()

		cr_note = self.create_sales_invoice(qty=-1, conversion_rate=75, rate=1, do_not_save=True)
		cr_note.cost_center = self.cost_center
		cr_note.is_return = 1
		cr_note.save().submit()

		# Reconcile
		pr = self.create_payment_reconciliation()
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_cr_note = self.get_journals_for(cr_note.doctype, cr_note.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 2)
		self.assertEqual(len(exc_je_for_cr_note), 2)
		self.assertEqual(exc_je_for_si, exc_je_for_cr_note)

		for x in exc_je_for_si + exc_je_for_cr_note:
			with self.subTest(x=x):
				self.assertEqual(
					[self.cost_center, self.cost_center],
					frappe.db.get_all(
						"Journal Entry Account", filters={"parent": x.parent}, pluck="cost_center"
					),
				)

		frappe.db.set_value("Company", self.company, "cost_center", cc)

	def setup_dimensions(self):
		# create dimension
		from erpnext.accounts.doctype.accounting_dimension.test_accounting_dimension import (
			create_dimension,
		)

		create_dimension()
		# make it non-mandatory
		loc = frappe.get_doc("Accounting Dimension", "Location")
		for x in loc.dimension_defaults:
			x.mandatory_for_bs = False
			x.mandatory_for_pl = False
		loc.save()

	def test_90_dimensions_filter(self):
		"""
		Test workings of dimension filters
		"""
		self.setup_dimensions()
		rate_in_account_currency = 1

		# Invoices
		si1 = self.create_sales_invoice(qty=1, rate=rate_in_account_currency, do_not_submit=True)
		si1.department = "Management - _TC"
		si1.save().submit()

		si2 = self.create_sales_invoice(qty=1, rate=rate_in_account_currency, do_not_submit=True)
		si2.department = "Operations - _TC"
		si2.save().submit()

		# Payments
		cr_note1 = self.create_sales_invoice(qty=-1, conversion_rate=75, rate=1, do_not_save=True)
		cr_note1.department = "Management - _TC"
		cr_note1.is_return = 1
		cr_note1.save().submit()

		cr_note2 = self.create_sales_invoice(qty=-1, conversion_rate=75, rate=1, do_not_save=True)
		cr_note2.department = "Legal - _TC"
		cr_note2.is_return = 1
		cr_note2.save().submit()

		pe1 = get_payment_entry(si1.doctype, si1.name)
		pe1.references = []
		pe1.department = "Research & Development - _TC"
		pe1.save().submit()

		pe2 = get_payment_entry(si1.doctype, si1.name)
		pe2.references = []
		pe2.department = "Management - _TC"
		pe2.save().submit()

		je1 = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=75,
			acc2=self.cash,
			acc1_amount=-1,
			acc2_amount=-75,
			acc2_exc_rate=1,
		)
		je1.accounts[0].party_type = "Customer"
		je1.accounts[0].party = self.customer
		je1.accounts[0].department = "Management - _TC"
		je1.save().submit()

		# assert dimension filter's result
		pr = self.create_payment_reconciliation()
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 2)
		self.assertEqual(len(pr.payments), 5)

		pr.department = "Legal - _TC"
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 1)

		pr.department = "Management - _TC"
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 3)

		pr.department = "Research & Development - _TC"
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 1)

	def test_91_cr_note_should_inherit_dimension(self):
		self.setup_dimensions()
		rate_in_account_currency = 1

		# Invoice
		si = self.create_sales_invoice(qty=1, rate=rate_in_account_currency, do_not_submit=True)
		si.department = "Management - _TC"
		si.save().submit()

		# Payment
		cr_note = self.create_sales_invoice(qty=-1, conversion_rate=75, rate=1, do_not_save=True)
		cr_note.department = "Management - _TC"
		cr_note.is_return = 1
		cr_note.save().submit()

		pr = self.create_payment_reconciliation()
		pr.department = "Management - _TC"
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# There should be 2 journals, JE(Cr Note) and JE(Exchange Gain/Loss)
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_cr_note = self.get_journals_for(cr_note.doctype, cr_note.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(len(exc_je_for_si), 2)
		self.assertEqual(len(exc_je_for_cr_note), 2)
		self.assertEqual(exc_je_for_si, exc_je_for_cr_note)

		for x in exc_je_for_si + exc_je_for_cr_note:
			with self.subTest(x=x):
				self.assertEqual(
					[cr_note.department, cr_note.department],
					frappe.db.get_all(
						"Journal Entry Account", filters={"parent": x.parent}, pluck="department"
					),
				)

	def test_92_dimension_inhertiance_exc_gain_loss(self):
		# Sales Invoice in Foreign Currency
		self.setup_dimensions()
		rate_in_account_currency = 1
		dpt = "Research & Development - _TC"

		si = self.create_sales_invoice(qty=1, rate=rate_in_account_currency, do_not_save=True)
		si.department = dpt
		si.save().submit()

		pe = self.create_payment_entry(amount=1, source_exc_rate=82).save()
		pe.department = dpt
		pe = pe.save().submit()

		pr = self.create_payment_reconciliation()
		pr.department = dpt
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# Exc Gain/Loss journals should inherit dimension from parent
		journals = self.get_journals_for(si.doctype, si.name)
		self.assertEqual(
			[dpt, dpt],
			frappe.db.get_all(
				"Journal Entry Account",
				filters={"parent": ("in", [x.parent for x in journals])},
				pluck="department",
			),
		)

	def test_93_dimension_inheritance_on_advance(self):
		self.setup_dimensions()
		dpt = "Research & Development - _TC"

		adv = self.create_payment_entry(amount=1, source_exc_rate=85)
		adv.department = dpt
		adv.save().submit()
		adv.reload()

		# Sales Invoices in different exchange rates
		si = self.create_sales_invoice(qty=1, conversion_rate=82, rate=1, do_not_submit=True)
		si.department = dpt
		advances = si.get_advance_entries()
		self.assertEqual(len(advances), 1)
		self.assertEqual(advances[0].reference_name, adv.name)
		si.append(
			"advances",
			{
				"doctype": "Sales Invoice Advance",
				"reference_type": advances[0].reference_type,
				"reference_name": advances[0].reference_name,
				"reference_row": advances[0].reference_row,
				"advance_amount": 1,
				"allocated_amount": 1,
				"ref_exchange_rate": advances[0].exchange_rate,
				"remarks": advances[0].remarks,
			},
		)
		si = si.save().submit()

		# Outstanding in both currencies should be '0'
		adv.reload()
		self.assertEqual(si.outstanding_amount, 0)
		self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

		# Exc Gain/Loss journals should inherit dimension from parent
		journals = self.get_journals_for(si.doctype, si.name)
		self.assertEqual(
			[dpt, dpt],
			frappe.db.get_all(
				"Journal Entry Account",
				filters={"parent": ("in", [x.parent for x in journals])},
				pluck="department",
			),
		)

	def test_50_journal_against_journal(self):
		# Invoice in Foreign Currency
		journal_as_invoice = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=83,
			acc2=self.cash,
			acc1_amount=1,
			acc2_amount=83,
			acc2_exc_rate=1,
		)
		journal_as_invoice.accounts[0].party_type = "Customer"
		journal_as_invoice.accounts[0].party = self.customer
		journal_as_invoice = journal_as_invoice.save().submit()

		# Payment
		journal_as_payment = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=75,
			acc2=self.cash,
			acc1_amount=-1,
			acc2_amount=-75,
			acc2_exc_rate=1,
		)
		journal_as_payment.accounts[0].party_type = "Customer"
		journal_as_payment.accounts[0].party = self.customer
		journal_as_payment = journal_as_payment.save().submit()

		# Reconcile the remaining amount
		pr = self.create_payment_reconciliation()
		# pr.receivable_payable_account = self.debit_usd
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# There should be no outstanding in both currencies
		journal_as_invoice.reload()
		self.assert_ledger_outstanding(journal_as_invoice.doctype, journal_as_invoice.name, 0.0, 0.0)

		# Exchange Gain/Loss Journal should've been created.
		exc_je_for_si = self.get_journals_for(journal_as_invoice.doctype, journal_as_invoice.name)
		exc_je_for_je = self.get_journals_for(journal_as_payment.doctype, journal_as_payment.name)
		self.assertNotEqual(exc_je_for_si, [])
		self.assertEqual(
			len(exc_je_for_si), 2
		)  # payment also has reference. so, there are 2 journals referencing invoice
		self.assertEqual(len(exc_je_for_je), 1)
		self.assertIn(exc_je_for_je[0], exc_je_for_si)

		# Cancel Payment
		journal_as_payment.reload()
		journal_as_payment.cancel()

		journal_as_invoice.reload()
		self.assert_ledger_outstanding(journal_as_invoice.doctype, journal_as_invoice.name, 83.0, 1.0)

		# Exchange Gain/Loss Journal should've been cancelled
		exc_je_for_si = self.get_journals_for(journal_as_invoice.doctype, journal_as_invoice.name)
		exc_je_for_je = self.get_journals_for(journal_as_payment.doctype, journal_as_payment.name)
		self.assertEqual(exc_je_for_si, [])
		self.assertEqual(exc_je_for_je, [])

	def test_60_payment_entry_against_journal(self):
		# Invoices
		exc_rate1 = 75
		exc_rate2 = 77
		amount = 1
		je1 = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=exc_rate1,
			acc2=self.cash,
			acc1_amount=amount,
			acc2_amount=(amount * 75),
			acc2_exc_rate=1,
		)
		je1.accounts[0].party_type = "Customer"
		je1.accounts[0].party = self.customer
		je1 = je1.save().submit()

		je2 = self.create_journal_entry(
			acc1=self.debit_usd,
			acc1_exc_rate=exc_rate2,
			acc2=self.cash,
			acc1_amount=amount,
			acc2_amount=(amount * exc_rate2),
			acc2_exc_rate=1,
		)
		je2.accounts[0].party_type = "Customer"
		je2.accounts[0].party = self.customer
		je2 = je2.save().submit()

		# Payment
		pe = self.create_payment_entry(amount=2, source_exc_rate=exc_rate1).save().submit()

		pr = self.create_payment_reconciliation()
		pr.receivable_payable_account = self.debit_usd
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 2)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# There should be no outstanding in both currencies
		self.assert_ledger_outstanding(je1.doctype, je1.name, 0.0, 0.0)
		self.assert_ledger_outstanding(je2.doctype, je2.name, 0.0, 0.0)

		# Exchange Gain/Loss Journal should've been created only for JE2
		exc_je_for_je1 = self.get_journals_for(je1.doctype, je1.name)
		exc_je_for_je2 = self.get_journals_for(je2.doctype, je2.name)
		self.assertEqual(exc_je_for_je1, [])
		self.assertEqual(len(exc_je_for_je2), 1)

		# Cancel Payment
		pe.reload()
		pe.cancel()

		self.assert_ledger_outstanding(je1.doctype, je1.name, (amount * exc_rate1), amount)
		self.assert_ledger_outstanding(je2.doctype, je2.name, (amount * exc_rate2), amount)

		# Exchange Gain/Loss Journal should've been cancelled
		exc_je_for_je1 = self.get_journals_for(je1.doctype, je1.name)
		exc_je_for_je2 = self.get_journals_for(je2.doctype, je2.name)
		self.assertEqual(exc_je_for_je1, [])
		self.assertEqual(exc_je_for_je2, [])

	def test_61_payment_entry_against_journal_for_payable_accounts(self):
		# Invoices
		exc_rate1 = 75
		exc_rate2 = 77
		amount = 1
		je1 = self.create_journal_entry(
			acc1=self.creditors_usd,
			acc1_exc_rate=exc_rate1,
			acc2=self.cash,
			acc1_amount=-amount,
			acc2_amount=(-amount * 75),
			acc2_exc_rate=1,
		)
		je1.accounts[0].party_type = "Supplier"
		je1.accounts[0].party = self.supplier
		je1 = je1.save().submit()

		# Payment
		pe = create_payment_entry(
			company=self.company,
			payment_type="Pay",
			party_type="Supplier",
			party=self.supplier,
			paid_from=self.cash,
			paid_to=self.creditors_usd,
			paid_amount=amount,
		)
		pe.target_exchange_rate = exc_rate2
		pe.received_amount = amount
		pe.paid_amount = amount * exc_rate2
		pe.save().submit()

		pr = frappe.get_doc(
			{
				"doctype": "Payment Reconciliation",
				"company": self.company,
				"party_type": "Supplier",
				"party": self.supplier,
				"receivable_payable_account": get_party_account("Supplier", self.supplier, self.company),
			}
		)
		pr.from_invoice_date = pr.to_invoice_date = pr.from_payment_date = pr.to_payment_date = nowdate()
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.invoices), 1)
		self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)

		# There should be no outstanding in both currencies
		self.assert_ledger_outstanding(je1.doctype, je1.name, 0.0, 0.0)

		# Exchange Gain/Loss Journal should've been created
		exc_je_for_je1 = self.get_journals_for(je1.doctype, je1.name)
		self.assertEqual(len(exc_je_for_je1), 1)

		# Cancel Payment
		pe.reload()
		pe.cancel()

		self.assert_ledger_outstanding(je1.doctype, je1.name, (amount * exc_rate1), amount)

		# Exchange Gain/Loss Journal should've been cancelled
		exc_je_for_je1 = self.get_journals_for(je1.doctype, je1.name)
		self.assertEqual(exc_je_for_je1, [])

	def test_70_advance_payment_against_sales_invoice_in_foreign_currency(self):
		"""
		Customer advance booked under Liability
		"""
		self.setup_advance_accounts_in_party_master()

		adv = self.create_payment_entry(amount=1, source_exc_rate=83)
		adv.save()  # explicit 'save' is needed to trigger set_liability_account()
		self.assertEqual(adv.paid_from, self.advance_received_usd)
		adv.submit()

		si = self.create_sales_invoice(qty=1, conversion_rate=80, rate=1, do_not_submit=True)
		si.debit_to = self.debtors_usd
		si.save().submit()
		self.assert_ledger_outstanding(si.doctype, si.name, 80.0, 1.0)

		pr = self.create_payment_reconciliation()
		pr.receivable_payable_account = self.debtors_usd
		pr.default_advance_account = self.advance_received_usd
		pr.get_unreconciled_entries()
		self.assertEqual(pr.invoices[0].invoice_number, si.name)
		self.assertEqual(pr.payments[0].reference_name, adv.name)

		# Allocate and Reconcile
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)
		self.assert_ledger_outstanding(si.doctype, si.name, 0.0, 0.0)

		# Exc Gain/Loss journal should've been creatad
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_adv), 1)
		self.assertEqual(exc_je_for_si, exc_je_for_adv)

		adv.reload()
		adv.cancel()
		si.reload()
		self.assert_ledger_outstanding(si.doctype, si.name, 80.0, 1.0)
		# Exc Gain/Loss journal should've been cancelled
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		self.assertEqual(len(exc_je_for_si), 0)
		self.assertEqual(len(exc_je_for_adv), 0)

		self.remove_advance_accounts_from_party_master()

	def test_71_advance_payment_against_purchase_invoice_in_foreign_currency(self):
		"""
		Supplier advance booked under Asset
		"""
		self.setup_advance_accounts_in_party_master()

		usd_amount = 1
		inr_amount = 85
		exc_rate = 85
		adv = create_payment_entry(
			company=self.company,
			payment_type="Pay",
			party_type="Supplier",
			party=self.supplier,
			paid_from=self.cash,
			paid_to=self.advance_paid_usd,
			paid_amount=inr_amount,
		)
		adv.source_exchange_rate = 1
		adv.target_exchange_rate = exc_rate
		adv.received_amount = usd_amount
		adv.paid_amount = exc_rate * usd_amount
		adv.posting_date = nowdate()
		adv.save()
		# Make sure that advance account is still set
		self.assertEqual(adv.paid_to, self.advance_paid_usd)
		adv.submit()

		pi = self.create_purchase_invoice(qty=1, conversion_rate=83, rate=1)
		self.assertEqual(pi.credit_to, self.creditors_usd)
		self.assert_ledger_outstanding(pi.doctype, pi.name, 83.0, 1.0)

		pr = self.create_payment_reconciliation()
		pr.party_type = "Supplier"
		pr.party = self.supplier
		pr.receivable_payable_account = self.creditors_usd
		pr.default_advance_account = self.advance_paid_usd
		pr.get_unreconciled_entries()
		self.assertEqual(pr.invoices[0].invoice_number, pi.name)
		self.assertEqual(pr.payments[0].reference_name, adv.name)

		# Allocate and Reconcile
		invoices = [x.as_dict() for x in pr.invoices]
		payments = [x.as_dict() for x in pr.payments]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()
		self.assertEqual(len(pr.invoices), 0)
		self.assertEqual(len(pr.payments), 0)
		self.assert_ledger_outstanding(pi.doctype, pi.name, 0.0, 0.0)

		# Exc Gain/Loss journal should've been creatad
		exc_je_for_pi = self.get_journals_for(pi.doctype, pi.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		self.assertEqual(len(exc_je_for_pi), 1)
		self.assertEqual(len(exc_je_for_adv), 1)
		self.assertEqual(exc_je_for_pi, exc_je_for_adv)

		adv.reload()
		adv.cancel()
		pi.reload()
		self.assert_ledger_outstanding(pi.doctype, pi.name, 83.0, 1.0)
		# Exc Gain/Loss journal should've been cancelled
		exc_je_for_pi = self.get_journals_for(pi.doctype, pi.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		self.assertEqual(len(exc_je_for_pi), 0)
		self.assertEqual(len(exc_je_for_adv), 0)

		self.remove_advance_accounts_from_party_master()

	def test_difference_posting_date_in_pi_and_si(self):
		self.setup_advance_accounts_in_party_master()

		# create payment entry for customer
		adv = self.create_payment_entry(amount=1, source_exc_rate=83)
		adv.save()
		self.assertEqual(adv.paid_from, self.advance_received_usd)
		adv.submit()
		adv.reload()

		# create sales invoice with advance received
		si = self.create_sales_invoice(qty=1, conversion_rate=80, rate=1, do_not_submit=True)
		si.debit_to = self.debtors_usd
		si.append(
			"advances",
			{
				"reference_type": adv.doctype,
				"reference_name": adv.name,
				"remarks": "Amount INR 1 received from _Test MC Customer USD\nTransaction reference no Test001 dated 2024-12-19",
				"advance_amount": 1.0,
				"allocated_amount": 1.0,
				"exchange_gain_loss": 3.0,
				"ref_exchange_rate": 83.0,
				"difference_posting_date": add_days(nowdate(), -2),
			},
		)
		si.save().submit()

		# exc Gain/Loss journal should've been creatad
		exc_je_for_si = self.get_journals_for(si.doctype, si.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		self.assertEqual(len(exc_je_for_si), 1)
		self.assertEqual(len(exc_je_for_adv), 1)
		self.assertEqual(exc_je_for_si, exc_je_for_adv)

		# check jv created with difference_posting_date in sales invoice
		jv = frappe.get_doc("Journal Entry", exc_je_for_si[0].parent)
		sales_invoice = frappe.get_doc("Sales Invoice", si.name)
		self.assertEqual(sales_invoice.advances[0].difference_posting_date, jv.posting_date)

		# create payment entry for supplier
		usd_amount = 1
		inr_amount = 85
		exc_rate = 85
		adv = create_payment_entry(
			company=self.company,
			payment_type="Pay",
			party_type="Supplier",
			party=self.supplier,
			paid_from=self.cash,
			paid_to=self.advance_paid_usd,
			paid_amount=inr_amount,
		)
		adv.source_exchange_rate = 1
		adv.target_exchange_rate = exc_rate
		adv.received_amount = usd_amount
		adv.paid_amount = exc_rate * usd_amount
		adv.posting_date = nowdate()
		adv.save()
		self.assertEqual(adv.paid_to, self.advance_paid_usd)
		adv.submit()

		# create purchase invoice with advance paid
		pi = self.create_purchase_invoice(qty=1, conversion_rate=80, rate=1, do_not_submit=True)
		pi.append(
			"advances",
			{
				"reference_type": adv.doctype,
				"reference_name": adv.name,
				"remarks": "Amount INR 1 paid to _Test MC Supplier USD\nTransaction reference no Test001 dated 2024-12-20",
				"advance_amount": 1.0,
				"allocated_amount": 1.0,
				"exchange_gain_loss": 5.0,
				"ref_exchange_rate": 85.0,
				"difference_posting_date": add_days(nowdate(), -2),
			},
		)
		pi.save().submit()
		self.assertEqual(pi.credit_to, self.creditors_usd)

		# exc Gain/Loss journal should've been creatad
		exc_je_for_pi = self.get_journals_for(pi.doctype, pi.name)
		exc_je_for_adv = self.get_journals_for(adv.doctype, adv.name)
		self.assertEqual(len(exc_je_for_pi), 1)
		self.assertEqual(len(exc_je_for_adv), 1)
		self.assertEqual(exc_je_for_pi, exc_je_for_adv)

		# check jv created with difference_posting_date in purchase invoice
		journal_voucher = frappe.get_doc("Journal Entry", exc_je_for_pi[0].parent)
		purchase_invoice = frappe.get_doc("Purchase Invoice", pi.name)
		self.assertEqual(purchase_invoice.advances[0].difference_posting_date, journal_voucher.posting_date)

	def test_company_validation_in_dimension(self):
		si = create_sales_invoice(do_not_submit=True)
		project = make_project({"project_name": "_Test Demo Project1", "company": "_Test Company 1"})
		si.project = project.name
		self.assertRaises(frappe.ValidationError, si.save)

		si_1 = create_sales_invoice(do_not_submit=True)
		si_1.items[0].project = project.name
		self.assertRaises(frappe.ValidationError, si_1.save)

	def test_party_billing_and_shipping_address(self):
		from erpnext.crm.doctype.prospect.test_prospect import make_address

		customer_billing = make_address(address_title="Customer")
		customer_billing.append("links", {"link_doctype": "Customer", "link_name": "_Test Customer"})
		customer_billing.save()
		supplier_billing = make_address(address_title="Supplier", address_line1="2", city="Ahmedabad")
		supplier_billing.append("links", {"link_doctype": "Supplier", "link_name": "_Test Supplier"})
		supplier_billing.save()

		customer_shipping = make_address(
			address_title="Customer", address_type="Shipping", address_line1="10"
		)
		customer_shipping.append("links", {"link_doctype": "Customer", "link_name": "_Test Customer"})
		customer_shipping.save()
		supplier_shipping = make_address(
			address_title="Supplier", address_type="Shipping", address_line1="20", city="Ahmedabad"
		)
		supplier_shipping.append("links", {"link_doctype": "Supplier", "link_name": "_Test Supplier"})
		supplier_shipping.save()

		si = create_sales_invoice(do_not_save=True)
		si.customer_address = supplier_billing.name
		self.assertRaises(frappe.ValidationError, si.save)
		si.customer_address = customer_billing.name
		si.save()

		si.shipping_address_name = supplier_shipping.name
		self.assertRaises(frappe.ValidationError, si.save)
		si.shipping_address_name = customer_shipping.name
		si.reload()
		si.save()

		pi = make_purchase_invoice(do_not_save=True)
		pi.supplier_address = customer_shipping.name
		self.assertRaises(frappe.ValidationError, pi.save)
		pi.supplier_address = supplier_shipping.name
		pi.save()

	def test_party_contact(self):
		from frappe.contacts.doctype.contact.test_contact import create_contact

		customer_contact = create_contact(name="Customer", salutation="Mr", save=False)
		customer_contact.append("links", {"link_doctype": "Customer", "link_name": "_Test Customer"})
		customer_contact.save()

		supplier_contact = create_contact(name="Supplier", salutation="Mr", save=False)
		supplier_contact.append("links", {"link_doctype": "Supplier", "link_name": "_Test Supplier"})
		supplier_contact.save()

		si = create_sales_invoice(do_not_save=True)
		si.contact_person = supplier_contact.name
		self.assertRaises(frappe.ValidationError, si.save)
		si.contact_person = customer_contact.name
		si.save()

	def test_discount_amount_not_mapped_repeatedly_for_sales_transactions(self):
		"""
		Test that additional discount amount is not copied repeatedly
		when creating multiple delivery notes from a single sales order with discount_amount set
		"""
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		# Create a sales order with discount amount
		so = make_sales_order(qty=10, rate=100, do_not_submit=True)
		so.apply_discount_on = "Net Total"
		so.discount_amount = 100
		so.save()
		so.submit()

		# Create first delivery note from sales order (partial qty)
		dn1 = make_delivery_note(so.name)
		dn1.items[0].qty = 5
		dn1.save()
		dn1.submit()

		# First delivery note should have full discount amount
		self.assertEqual(dn1.discount_amount, 100)
		self.assertEqual(dn1.grand_total, 400)

		# Create second delivery note from the same sales order (remaining qty)
		dn2 = make_delivery_note(so.name)
		dn2.items[0].qty = 5
		dn2.save()
		dn2.submit()

		# Second delivery note should have discount_amount set to 0
		# because discount was already fully applied in first delivery note
		self.assertEqual(dn2.discount_amount, 0)
		self.assertEqual(dn2.grand_total, 500)

	def test_discount_amount_not_mapped_repeatedly_for_purchase_transactions(self):
		"""
		Test that additional discount amount is not copied repeatedly
		when creating multiple purchase receipts from a single purchase order with discount_amount set
		"""
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		# Create a purchase order with discount amount
		po = create_purchase_order(qty=10, rate=100, do_not_submit=True)
		po.apply_discount_on = "Net Total"
		po.discount_amount = 100
		po.save()
		po.submit()

		# Create first purchase receipt from purchase order (partial qty)
		pr1 = make_purchase_receipt(po.name)
		pr1.items[0].qty = 5
		pr1.save()
		pr1.submit()

		# First purchase receipt should have full discount amount
		self.assertEqual(pr1.discount_amount, 100)
		self.assertEqual(pr1.grand_total, 400)

		# Create second purchase receipt from the same purchase order (remaining qty)
		pr2 = make_purchase_receipt(po.name)
		pr2.items[0].qty = 5
		pr2.save()
		pr2.submit()

		# Second purchase receipt should have discount_amount set to 0
		# because discount was already fully applied in first purchase receipt
		self.assertEqual(pr2.discount_amount, 0)
		self.assertEqual(pr2.grand_total, 500)

	def test_discount_amount_partial_application_in_mapped_transactions(self):
		"""
		Test that discount amount is partially applied when some discount
		has already been used in previous mapped transactions
		"""
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		# Create a sales order with discount amount
		so = make_sales_order(qty=10, rate=100, do_not_submit=True)
		so.apply_discount_on = "Net Total"
		so.discount_amount = 200
		so.save()
		so.submit()

		self.assertEqual(so.discount_amount, 200)
		self.assertEqual(so.grand_total, 800)

		# Create first invoice with partial discount (manually set lower discount)
		si1 = make_sales_invoice(so.name)
		si1.items[0].qty = 5
		si1.discount_amount = 50  # Partial discount application
		si1.save()
		si1.submit()

		self.assertEqual(si1.discount_amount, 50)
		self.assertEqual(si1.grand_total, 450)

		# Create second invoice from the same sales order
		si2 = make_sales_invoice(so.name)
		si2.items[0].qty = 5
		si2.save()
		si2.submit()

		# Second invoice should have remaining discount (200 - 50 = 150)
		self.assertEqual(si2.discount_amount, 150)
		self.assertEqual(si2.grand_total, 350)

	def test_discount_amount_not_mapped_when_percentage_is_set(self):
		"""
		Test that discount amount is not adjusted when additional_discount_percentage
		is set in the source document (as it will be recalculated based on percentage)
		"""
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		# Create a sales order with discount percentage instead of amount
		so = make_sales_order(qty=10, rate=100, do_not_submit=True)
		so.apply_discount_on = "Net Total"
		so.additional_discount_percentage = 10  # 10% discount
		so.save()
		so.submit()

		self.assertEqual(so.discount_amount, 100)  # 10% of 1000
		self.assertEqual(so.grand_total, 900)

		# Create delivery note from sales order
		dn = make_delivery_note(so.name)
		dn.items[0].qty = 5
		dn.save()

		# Delivery note should have discount amount recalculated based on percentage
		# and not affected by the repeated mapping logic
		self.assertEqual(dn.additional_discount_percentage, 10)
		self.assertEqual(dn.discount_amount, 50)  # 10% of 500

	def test_discount_amount_for_multiple_returns(self):
		"""
		Test that discount amount is correctly adjusted when multiple return invoices
		are created against the same original invoice to prevent over-returning discount
		"""
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

		# Create original sales invoice with discount
		si = create_sales_invoice(qty=10, rate=100, do_not_submit=True)
		si.apply_discount_on = "Net Total"
		si.discount_amount = 100
		si.save()
		si.submit()

		# Create first return - Frappe will copy full discount by default, we need to adjust it
		return_si_1 = make_sales_return(si.name)
		return_si_1.items[0].qty = -6  # Return 6 out of 10 items
		# Manually set discount to match the proportion (60% of discount)
		return_si_1.discount_amount = -60
		return_si_1.save()
		return_si_1.submit()

		self.assertEqual(return_si_1.discount_amount, -60)

		# Create second return for remaining items
		return_si_2 = make_sales_return(si.name)
		return_si_2.items[0].qty = -4  # Return remaining 4 out of 10 items
		return_si_2.save()

		# Second return should only get remaining discount (100 - 60 = 40)
		self.assertEqual(return_si_2.discount_amount, -40)

	def test_company_linked_address(self):
		from erpnext.crm.doctype.prospect.test_prospect import make_address

		company_address = make_address(
			address_title="Company", address_type="Shipping", address_line1="100", city="Mumbai"
		)
		company_address.append("links", {"link_doctype": "Company", "link_name": "_Test Company"})
		company_address.save()

		customer_shipping = make_address(
			address_title="Customer", address_type="Shipping", address_line1="10"
		)
		customer_shipping.append("links", {"link_doctype": "Customer", "link_name": "_Test Customer"})
		customer_shipping.save()

		supplier_billing = make_address(address_title="Supplier", address_line1="2", city="Ahmedabad")
		supplier_billing.append("links", {"link_doctype": "Supplier", "link_name": "_Test Supplier"})
		supplier_billing.save()

		po = create_purchase_order(do_not_save=True)
		po.shipping_address = customer_shipping.name
		self.assertRaises(frappe.ValidationError, po.save)
		po.shipping_address = company_address.name
		po.save()

		po.billing_address = supplier_billing.name
		self.assertRaises(frappe.ValidationError, po.save)
		po.billing_address = company_address.name
		po.reload()
		po.save()
