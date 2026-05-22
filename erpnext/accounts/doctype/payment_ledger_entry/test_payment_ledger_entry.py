# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import qb
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.tests.utils import ERPNextTestSuite


class TestPaymentLedgerEntry(ERPNextTestSuite):
	def setUp(self):
		self.ple = qb.DocType("Payment Ledger Entry")
		self.create_company()
		self.create_item()
		self.create_customer()
		self.clear_old_entries()

	def create_company(self):
		company_name = "_Test Payment Ledger"
		company = None
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
		item_name = "_Test PL Item"
		item = create_item(
			item_code=item_name, is_stock_item=0, company=self.company, warehouse=self.warehouse
		)
		self.item = item if isinstance(item, str) else item.item_code

	def create_customer(self):
		name = "_Test PL Customer"
		if frappe.db.exists("Customer", name):
			self.customer = name
		else:
			customer = frappe.new_doc("Customer")
			customer.customer_name = name
			customer.type = "Individual"
			customer.save()
			self.customer = customer.name

	def create_sales_invoice(
		self, qty=1, rate=100, posting_date=None, do_not_save=False, do_not_submit=False
	):
		"""
		Helper function to populate default values in sales invoice
		"""
		if posting_date is None:
			posting_date = nowdate()

		sinv = create_sales_invoice(
			posting_date=posting_date,
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

	def create_payment_entry(self, amount=100, posting_date=None):
		"""
		Helper function to populate default values in payment entry
		"""
		if posting_date is None:
			posting_date = nowdate()
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

	def create_sales_order(self, qty=1, rate=100, posting_date=None, do_not_save=False, do_not_submit=False):
		if posting_date is None:
			posting_date = nowdate()

		so = make_sales_order(
			company=self.company,
			transaction_date=posting_date,
			customer=self.customer,
			item_code=self.item,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			currency="INR",
			qty=qty,
			rate=100,
			do_not_save=do_not_save,
			do_not_submit=do_not_submit,
		)
		return so

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

	def test_payment_against_invoice(self):
		transaction_date = nowdate()
		amount = 100
		ple = self.ple

		# full payment using PE
		si1 = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		pe1 = get_payment_entry(si1.doctype, si1.name).save().submit()

		pl_entries = (
			qb.from_(ple)
			.select(
				ple.voucher_type,
				ple.voucher_no,
				ple.against_voucher_type,
				ple.against_voucher_no,
				ple.amount,
				ple.delinked,
			)
			.where((ple.against_voucher_type == si1.doctype) & (ple.against_voucher_no == si1.name))
			.orderby(ple.creation)
			.run(as_dict=True)
		)

		expected_values = [
			{
				"voucher_type": si1.doctype,
				"voucher_no": si1.name,
				"against_voucher_type": si1.doctype,
				"against_voucher_no": si1.name,
				"amount": amount,
				"delinked": 0,
			},
			{
				"voucher_type": pe1.doctype,
				"voucher_no": pe1.name,
				"against_voucher_type": si1.doctype,
				"against_voucher_no": si1.name,
				"amount": -amount,
				"delinked": 0,
			},
		]
		self.assertEqual(pl_entries[0], expected_values[0])
		self.assertEqual(pl_entries[1], expected_values[1])

	def test_partial_payment_against_invoice(self):
		ple = self.ple
		transaction_date = nowdate()
		amount = 100

		# partial payment of invoice using PE
		si2 = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		pe2 = get_payment_entry(si2.doctype, si2.name)
		pe2.get("references")[0].allocated_amount = 50
		pe2.get("references")[0].outstanding_amount = 50
		pe2 = pe2.save().submit()

		pl_entries = (
			qb.from_(ple)
			.select(
				ple.voucher_type,
				ple.voucher_no,
				ple.against_voucher_type,
				ple.against_voucher_no,
				ple.amount,
				ple.delinked,
			)
			.where((ple.against_voucher_type == si2.doctype) & (ple.against_voucher_no == si2.name))
			.orderby(ple.creation)
			.run(as_dict=True)
		)

		expected_values = [
			{
				"voucher_type": si2.doctype,
				"voucher_no": si2.name,
				"against_voucher_type": si2.doctype,
				"against_voucher_no": si2.name,
				"amount": amount,
				"delinked": 0,
			},
			{
				"voucher_type": pe2.doctype,
				"voucher_no": pe2.name,
				"against_voucher_type": si2.doctype,
				"against_voucher_no": si2.name,
				"amount": -50,
				"delinked": 0,
			},
		]
		self.assertEqual(pl_entries[0], expected_values[0])
		self.assertEqual(pl_entries[1], expected_values[1])

	def test_cr_note_against_invoice(self):
		ple = self.ple
		transaction_date = nowdate()
		amount = 100

		# reconcile against return invoice
		si3 = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		cr_note1 = self.create_sales_invoice(
			qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		cr_note1.is_return = 1
		cr_note1.return_against = si3.name
		cr_note1 = cr_note1.save().submit()

		pl_entries_si3 = (
			qb.from_(ple)
			.select(
				ple.voucher_type,
				ple.voucher_no,
				ple.against_voucher_type,
				ple.against_voucher_no,
				ple.amount,
				ple.delinked,
			)
			.where((ple.against_voucher_type == si3.doctype) & (ple.against_voucher_no == si3.name))
			.orderby(ple.creation)
			.run(as_dict=True)
		)

		pl_entries_cr_note1 = (
			qb.from_(ple)
			.select(
				ple.voucher_type,
				ple.voucher_no,
				ple.against_voucher_type,
				ple.against_voucher_no,
				ple.amount,
				ple.delinked,
			)
			.where((ple.against_voucher_type == cr_note1.doctype) & (ple.against_voucher_no == cr_note1.name))
			.orderby(ple.creation)
			.run(as_dict=True)
		)

		expected_values_for_si3 = [
			{
				"voucher_type": si3.doctype,
				"voucher_no": si3.name,
				"against_voucher_type": si3.doctype,
				"against_voucher_no": si3.name,
				"amount": amount,
				"delinked": 0,
			}
		]
		# credit/debit notes post ledger entries against itself
		expected_values_for_cr_note1 = [
			{
				"voucher_type": cr_note1.doctype,
				"voucher_no": cr_note1.name,
				"against_voucher_type": cr_note1.doctype,
				"against_voucher_no": cr_note1.name,
				"amount": -amount,
				"delinked": 0,
			},
		]
		self.assertEqual(pl_entries_si3, expected_values_for_si3)
		self.assertEqual(pl_entries_cr_note1, expected_values_for_cr_note1)

	def test_je_against_inv_and_note(self):
		ple = self.ple
		transaction_date = nowdate()
		amount = 100

		# reconcile against return invoice using JE
		si4 = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)
		cr_note2 = self.create_sales_invoice(
			qty=-1, rate=amount, posting_date=transaction_date, do_not_save=True, do_not_submit=True
		)
		cr_note2.is_return = 1
		cr_note2 = cr_note2.save().submit()
		je1 = self.create_journal_entry(self.debit_to, self.debit_to, amount, posting_date=transaction_date)
		je1.get("accounts")[0].party_type = je1.get("accounts")[1].party_type = "Customer"
		je1.get("accounts")[0].party = je1.get("accounts")[1].party = self.customer
		je1.get("accounts")[0].reference_type = cr_note2.doctype
		je1.get("accounts")[0].reference_name = cr_note2.name
		je1.get("accounts")[1].reference_type = si4.doctype
		je1.get("accounts")[1].reference_name = si4.name
		je1 = je1.save().submit()

		pl_entries_for_invoice = (
			qb.from_(ple)
			.select(
				ple.voucher_type,
				ple.voucher_no,
				ple.against_voucher_type,
				ple.against_voucher_no,
				ple.amount,
				ple.delinked,
			)
			.where((ple.against_voucher_type == si4.doctype) & (ple.against_voucher_no == si4.name))
			.orderby(ple.creation)
			.run(as_dict=True)
		)

		expected_values = [
			{
				"voucher_type": si4.doctype,
				"voucher_no": si4.name,
				"against_voucher_type": si4.doctype,
				"against_voucher_no": si4.name,
				"amount": amount,
				"delinked": 0,
			},
			{
				"voucher_type": je1.doctype,
				"voucher_no": je1.name,
				"against_voucher_type": si4.doctype,
				"against_voucher_no": si4.name,
				"amount": -amount,
				"delinked": 0,
			},
		]
		self.assertEqual(pl_entries_for_invoice[0], expected_values[0])
		self.assertEqual(pl_entries_for_invoice[1], expected_values[1])

		pl_entries_for_crnote = (
			qb.from_(ple)
			.select(
				ple.voucher_type,
				ple.voucher_no,
				ple.against_voucher_type,
				ple.against_voucher_no,
				ple.amount,
				ple.delinked,
			)
			.where((ple.against_voucher_type == cr_note2.doctype) & (ple.against_voucher_no == cr_note2.name))
			.orderby(ple.creation)
			.run(as_dict=True)
		)

		expected_values = [
			{
				"voucher_type": cr_note2.doctype,
				"voucher_no": cr_note2.name,
				"against_voucher_type": cr_note2.doctype,
				"against_voucher_no": cr_note2.name,
				"amount": -amount,
				"delinked": 0,
			},
			{
				"voucher_type": je1.doctype,
				"voucher_no": je1.name,
				"against_voucher_type": cr_note2.doctype,
				"against_voucher_no": cr_note2.name,
				"amount": amount,
				"delinked": 0,
			},
		]
		self.assertEqual(pl_entries_for_crnote[0], expected_values[0])
		self.assertEqual(pl_entries_for_crnote[1], expected_values[1])

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{"unlink_payment_on_cancellation_of_invoice": 1, "delete_linked_ledger_entries": 1},
	)
	def test_multi_payment_unlink_on_invoice_cancellation(self):
		transaction_date = nowdate()
		amount = 100
		si = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)

		for amt in [40, 40, 20]:
			# payment 1
			pe = get_payment_entry(si.doctype, si.name)
			pe.paid_amount = amt
			pe.get("references")[0].allocated_amount = amt
			pe = pe.save().submit()

		si.reload()
		si.cancel()

		entries = frappe.db.get_list(
			"Payment Ledger Entry",
			filters={"against_voucher_type": si.doctype, "against_voucher_no": si.name, "delinked": 0},
		)
		self.assertEqual(entries, [])

		# with references removed, deletion should be possible
		si.delete()
		self.assertRaises(frappe.DoesNotExistError, frappe.get_doc, si.doctype, si.name)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{"unlink_payment_on_cancellation_of_invoice": 1, "delete_linked_ledger_entries": 1},
	)
	def test_multi_je_unlink_on_invoice_cancellation(self):
		transaction_date = nowdate()
		amount = 100
		si = self.create_sales_invoice(qty=1, rate=amount, posting_date=transaction_date)

		# multiple JE's against invoice
		for amt in [40, 40, 20]:
			je1 = self.create_journal_entry(
				self.income_account, self.debit_to, amt, posting_date=transaction_date
			)
			je1.get("accounts")[1].party_type = "Customer"
			je1.get("accounts")[1].party = self.customer
			je1.get("accounts")[1].reference_type = si.doctype
			je1.get("accounts")[1].reference_name = si.name
			je1 = je1.save().submit()

		si.reload()
		si.cancel()

		entries = frappe.db.get_list(
			"Payment Ledger Entry",
			filters={"against_voucher_type": si.doctype, "against_voucher_no": si.name, "delinked": 0},
		)
		self.assertEqual(entries, [])

		# with references removed, deletion should be possible
		si.delete()
		self.assertRaises(frappe.DoesNotExistError, frappe.get_doc, si.doctype, si.name)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{
			"unlink_payment_on_cancellation_of_invoice": 1,
			"delete_linked_ledger_entries": 1,
			"unlink_advance_payment_on_cancelation_of_order": 1,
		},
	)
	def test_advance_payment_unlink_on_order_cancellation(self):
		transaction_date = nowdate()
		amount = 100
		so = self.create_sales_order(qty=1, rate=amount, posting_date=transaction_date).save().submit()

		get_payment_entry(so.doctype, so.name).save().submit()

		so.reload()
		so.cancel()

		entries = frappe.db.get_list(
			"Payment Ledger Entry",
			filters={"against_voucher_type": so.doctype, "against_voucher_no": so.name, "delinked": 0},
		)
		self.assertEqual(entries, [])

		# with references removed, deletion should be possible
		so.delete()
		self.assertRaises(frappe.DoesNotExistError, frappe.get_doc, so.doctype, so.name)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{"enable_immutable_ledger": 1},
	)
	def test_sales_invoice_cancellation_creates_reverse_entries_for_immutable_ledger(self):
		invoice_posting_date = add_days(nowdate(), -5)
		cancel_posting_date = nowdate()
		gle = qb.DocType("GL Entry")
		ple = qb.DocType("Payment Ledger Entry")

		si = self.create_sales_invoice(qty=1, rate=100, posting_date=invoice_posting_date)

		gle_before_cancel = (
			qb.from_(gle)
			.select(
				gle.account,
				gle.party_type,
				gle.party,
				gle.cost_center,
				gle.project,
				gle.finance_book,
				gle.posting_date,
				gle.debit,
				gle.credit,
				gle.debit_in_account_currency,
				gle.credit_in_account_currency,
			)
			.where((gle.voucher_type == si.doctype) & (gle.voucher_no == si.name) & (gle.is_cancelled == 0))
			.run(as_dict=True)
		)

		ple_before_cancel = (
			qb.from_(ple)
			.select(
				ple.name,
				ple.account_type,
				ple.account,
				ple.party_type,
				ple.party,
				ple.posting_date,
				ple.against_voucher_type,
				ple.against_voucher_no,
				ple.amount,
				ple.amount_in_account_currency,
				ple.delinked,
			)
			.where((ple.voucher_type == si.doctype) & (ple.voucher_no == si.name))
			.run(as_dict=True)
		)
		si.cancel()

		gle_after_cancel = (
			qb.from_(gle)
			.select(
				gle.account,
				gle.party_type,
				gle.party,
				gle.cost_center,
				gle.project,
				gle.finance_book,
				gle.posting_date,
				gle.debit,
				gle.credit,
				gle.debit_in_account_currency,
				gle.credit_in_account_currency,
			)
			.where((gle.voucher_type == si.doctype) & (gle.voucher_no == si.name) & (gle.is_cancelled == 0))
			.run(as_dict=True)
		)

		self.assertEqual(len(gle_after_cancel), len(gle_before_cancel) * 2)

		after_gl = [
			(
				d.account,
				d.party_type,
				d.party,
				d.cost_center,
				d.project,
				d.finance_book,
				str(d.posting_date),
				d.debit,
				d.credit,
				d.debit_in_account_currency,
				d.credit_in_account_currency,
			)
			for d in gle_after_cancel
		]
		for d in gle_before_cancel:
			self.assertIn(
				(
					d.account,
					d.party_type,
					d.party,
					d.cost_center,
					d.project,
					d.finance_book,
					cancel_posting_date,
					d.credit,
					d.debit,
					d.credit_in_account_currency,
					d.debit_in_account_currency,
				),
				after_gl,
			)

		ple_after_cancel = (
			qb.from_(ple)
			.select(
				ple.name,
				ple.account_type,
				ple.account,
				ple.party_type,
				ple.party,
				ple.posting_date,
				ple.against_voucher_type,
				ple.against_voucher_no,
				ple.amount,
				ple.amount_in_account_currency,
				ple.delinked,
			)
			.where((ple.voucher_type == si.doctype) & (ple.voucher_no == si.name))
			.run(as_dict=True)
		)

		self.assertEqual(len(ple_after_cancel), len(ple_before_cancel) * 2)

		after_ple = [
			(
				d.account_type,
				d.account,
				d.party_type,
				d.party,
				str(d.posting_date),
				d.against_voucher_type,
				d.against_voucher_no,
				d.amount,
				d.amount_in_account_currency,
				d.delinked,
			)
			for d in ple_after_cancel
		]
		for d in ple_before_cancel:
			self.assertIn(
				(
					d.account_type,
					d.account,
					d.party_type,
					d.party,
					cancel_posting_date,
					d.against_voucher_type,
					d.against_voucher_no,
					-d.amount,
					-d.amount_in_account_currency,
					0,
				),
				after_ple,
			)

		original_ple_names = [d.name for d in ple_before_cancel]
		self.assertFalse(
			frappe.db.exists(
				"Payment Ledger Entry",
				{"name": ("in", original_ple_names), "delinked": 1},
			)
		)
