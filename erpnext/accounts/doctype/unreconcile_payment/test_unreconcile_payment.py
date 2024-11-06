# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.party import get_party_account
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order


class TestUnreconcilePayment(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_usd_receivable_account()
		self.create_item()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def create_sales_invoice(self, do_not_submit=False):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			price_list_rate=100,
			do_not_submit=do_not_submit,
		)
		return si

	def create_payment_entry(self):
		pe = create_payment_entry(
			company=self.company,
			payment_type="Receive",
			party_type="Customer",
			party=self.customer,
			paid_from=self.debit_to,
			paid_to=self.cash,
			paid_amount=200,
			save=True,
		)
		return pe

	def create_sales_order(self):
		so = make_sales_order(
			company=self.company,
			customer=self.customer,
			item=self.item,
			rate=100,
			transaction_date=today(),
		)
		return so

	def test_01_unreconcile_invoice(self):
		si1 = self.create_sales_invoice()
		si2 = self.create_sales_invoice()

		pe = self.create_payment_entry()
		pe.append(
			"references",
			{"reference_doctype": si1.doctype, "reference_name": si1.name, "allocated_amount": 100},
		)
		pe.append(
			"references",
			{"reference_doctype": si2.doctype, "reference_name": si2.name, "allocated_amount": 100},
		)
		# Allocation payment against both invoices
		pe.save().submit()

		# Assert outstanding
		[doc.reload() for doc in [si1, si2, pe]]
		self.assertEqual(si1.outstanding_amount, 0)
		self.assertEqual(si2.outstanding_amount, 0)
		self.assertEqual(pe.unallocated_amount, 0)

		unreconcile = frappe.get_doc(
			{
				"doctype": "Unreconcile Payment",
				"company": self.company,
				"voucher_type": pe.doctype,
				"voucher_no": pe.name,
			}
		)
		unreconcile.add_references()
		self.assertEqual(len(unreconcile.allocations), 2)
		allocations = [x.reference_name for x in unreconcile.allocations]
		self.assertEqual([si1.name, si2.name], allocations)
		# unreconcile si1
		for x in unreconcile.allocations:
			if x.reference_name != si1.name:
				unreconcile.remove(x)
		unreconcile.save().submit()

		# Assert outstanding
		[doc.reload() for doc in [si1, si2, pe]]
		self.assertEqual(si1.outstanding_amount, 100)
		self.assertEqual(si2.outstanding_amount, 0)
		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.unallocated_amount, 100)

	def test_02_unreconcile_one_payment_among_multi_payments(self):
		"""
		Scenario: 2 payments, both split against 2 different invoices
		Unreconcile only one payment from one invoice
		"""
		si1 = self.create_sales_invoice()
		si2 = self.create_sales_invoice()
		pe1 = self.create_payment_entry()
		pe1.paid_amount = 100
		# Allocate payment against both invoices
		pe1.append(
			"references",
			{"reference_doctype": si1.doctype, "reference_name": si1.name, "allocated_amount": 50},
		)
		pe1.append(
			"references",
			{"reference_doctype": si2.doctype, "reference_name": si2.name, "allocated_amount": 50},
		)
		pe1.save().submit()

		pe2 = self.create_payment_entry()
		pe2.paid_amount = 100
		# Allocate payment against both invoices
		pe2.append(
			"references",
			{"reference_doctype": si1.doctype, "reference_name": si1.name, "allocated_amount": 50},
		)
		pe2.append(
			"references",
			{"reference_doctype": si2.doctype, "reference_name": si2.name, "allocated_amount": 50},
		)
		pe2.save().submit()

		# Assert outstanding and unallocated
		[doc.reload() for doc in [si1, si2, pe1, pe2]]
		self.assertEqual(si1.outstanding_amount, 0.0)
		self.assertEqual(si2.outstanding_amount, 0.0)
		self.assertEqual(pe1.unallocated_amount, 0.0)
		self.assertEqual(pe2.unallocated_amount, 0.0)

		unreconcile = frappe.get_doc(
			{
				"doctype": "Unreconcile Payment",
				"company": self.company,
				"voucher_type": pe2.doctype,
				"voucher_no": pe2.name,
			}
		)
		unreconcile.add_references()
		self.assertEqual(len(unreconcile.allocations), 2)
		allocations = [x.reference_name for x in unreconcile.allocations]
		self.assertEqual([si1.name, si2.name], allocations)
		# unreconcile si1 from pe2
		for x in unreconcile.allocations:
			if x.reference_name != si1.name:
				unreconcile.remove(x)
		unreconcile.save().submit()

		# Assert outstanding and unallocated
		[doc.reload() for doc in [si1, si2, pe1, pe2]]
		self.assertEqual(si1.outstanding_amount, 50)
		self.assertEqual(si2.outstanding_amount, 0)
		self.assertEqual(len(pe1.references), 2)
		self.assertEqual(len(pe2.references), 1)
		self.assertEqual(pe1.unallocated_amount, 0)
		self.assertEqual(pe2.unallocated_amount, 50)

	def test_03_unreconciliation_on_multi_currency_invoice(self):
		self.create_customer("_Test MC Customer USD", "USD")
		si1 = self.create_sales_invoice(do_not_submit=True)
		si1.currency = "USD"
		si1.debit_to = self.debtors_usd
		si1.conversion_rate = 80
		si1.save().submit()

		si2 = self.create_sales_invoice(do_not_submit=True)
		si2.currency = "USD"
		si2.debit_to = self.debtors_usd
		si2.conversion_rate = 80
		si2.save().submit()

		pe = self.create_payment_entry()
		pe.paid_from = self.debtors_usd
		pe.paid_from_account_currency = "USD"
		pe.source_exchange_rate = 75
		pe.received_amount = 75 * 200
		pe.save()
		# Allocate payment against both invoices
		pe.append(
			"references",
			{"reference_doctype": si1.doctype, "reference_name": si1.name, "allocated_amount": 100},
		)
		pe.append(
			"references",
			{"reference_doctype": si2.doctype, "reference_name": si2.name, "allocated_amount": 100},
		)
		pe.save().submit()

		unreconcile = frappe.get_doc(
			{
				"doctype": "Unreconcile Payment",
				"company": self.company,
				"voucher_type": pe.doctype,
				"voucher_no": pe.name,
			}
		)
		unreconcile.add_references()
		self.assertEqual(len(unreconcile.allocations), 2)
		allocations = [x.reference_name for x in unreconcile.allocations]
		self.assertEqual([si1.name, si2.name], allocations)
		# unreconcile si1 from pe
		for x in unreconcile.allocations:
			if x.reference_name != si1.name:
				unreconcile.remove(x)
		unreconcile.save().submit()

		# Assert outstanding and unallocated
		[doc.reload() for doc in [si1, si2, pe]]
		self.assertEqual(si1.outstanding_amount, 100)
		self.assertEqual(si2.outstanding_amount, 0)
		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.unallocated_amount, 100)

		# Exc gain/loss JE should've been cancelled as well
		self.assertEqual(
			frappe.db.count(
				"Journal Entry Account",
				filters={"reference_type": si1.doctype, "reference_name": si1.name, "docstatus": 1},
			),
			0,
		)

	def test_04_unreconciliation_on_multi_currency_invoice(self):
		"""
		2 payments split against 2 foreign currency invoices
		"""
		self.create_customer("_Test MC Customer USD", "USD")
		si1 = self.create_sales_invoice(do_not_submit=True)
		si1.currency = "USD"
		si1.debit_to = self.debtors_usd
		si1.conversion_rate = 80
		si1.save().submit()

		si2 = self.create_sales_invoice(do_not_submit=True)
		si2.currency = "USD"
		si2.debit_to = self.debtors_usd
		si2.conversion_rate = 80
		si2.save().submit()

		pe1 = self.create_payment_entry()
		pe1.paid_from = self.debtors_usd
		pe1.paid_from_account_currency = "USD"
		pe1.source_exchange_rate = 75
		pe1.received_amount = 75 * 100
		pe1.save()
		# Allocate payment against both invoices
		pe1.append(
			"references",
			{"reference_doctype": si1.doctype, "reference_name": si1.name, "allocated_amount": 50},
		)
		pe1.append(
			"references",
			{"reference_doctype": si2.doctype, "reference_name": si2.name, "allocated_amount": 50},
		)
		pe1.save().submit()

		pe2 = self.create_payment_entry()
		pe2.paid_from = self.debtors_usd
		pe2.paid_from_account_currency = "USD"
		pe2.source_exchange_rate = 75
		pe2.received_amount = 75 * 100
		pe2.save()
		# Allocate payment against both invoices
		pe2.append(
			"references",
			{"reference_doctype": si1.doctype, "reference_name": si1.name, "allocated_amount": 50},
		)
		pe2.append(
			"references",
			{"reference_doctype": si2.doctype, "reference_name": si2.name, "allocated_amount": 50},
		)
		pe2.save().submit()

		unreconcile = frappe.get_doc(
			{
				"doctype": "Unreconcile Payment",
				"company": self.company,
				"voucher_type": pe2.doctype,
				"voucher_no": pe2.name,
			}
		)
		unreconcile.add_references()
		self.assertEqual(len(unreconcile.allocations), 2)
		allocations = [x.reference_name for x in unreconcile.allocations]
		self.assertEqual([si1.name, si2.name], allocations)
		# unreconcile si1 from pe2
		for x in unreconcile.allocations:
			if x.reference_name != si1.name:
				unreconcile.remove(x)
		unreconcile.save().submit()

		# Assert outstanding and unallocated
		[doc.reload() for doc in [si1, si2, pe1, pe2]]
		self.assertEqual(si1.outstanding_amount, 50)
		self.assertEqual(si2.outstanding_amount, 0)
		self.assertEqual(len(pe1.references), 2)
		self.assertEqual(len(pe2.references), 1)
		self.assertEqual(pe1.unallocated_amount, 0)
		self.assertEqual(pe2.unallocated_amount, 50)

		# Exc gain/loss JE from PE1 should be available
		self.assertEqual(
			frappe.db.count(
				"Journal Entry Account",
				filters={"reference_type": si1.doctype, "reference_name": si1.name, "docstatus": 1},
			),
			1,
		)

	def test_05_unreconcile_order(self):
		so = self.create_sales_order()

		pe = self.create_payment_entry()
		# Allocation payment against Sales Order
		pe.paid_amount = 100
		pe.append(
			"references",
			{"reference_doctype": so.doctype, "reference_name": so.name, "allocated_amount": 100},
		)
		pe.save().submit()

		# Assert 'Advance Paid'
		so.reload()
		self.assertEqual(so.advance_paid, 100)

		unreconcile = frappe.get_doc(
			{
				"doctype": "Unreconcile Payment",
				"company": self.company,
				"voucher_type": pe.doctype,
				"voucher_no": pe.name,
			}
		)
		unreconcile.add_references()
		self.assertEqual(len(unreconcile.allocations), 1)
		allocations = [x.reference_name for x in unreconcile.allocations]
		self.assertEqual([so.name], allocations)
		# unreconcile so
		unreconcile.save().submit()

		# Assert 'Advance Paid'
		so.reload()
		pe.reload()
		self.assertEqual(so.advance_paid, 100)
		self.assertEqual(len(pe.references), 0)
		self.assertEqual(pe.unallocated_amount, 100)

		pe.cancel()
		so.reload()
		self.assertEqual(so.advance_paid, 100)

	def test_06_unreconcile_advance_from_payment_entry(self):
		self.enable_advance_as_liability()
		so1 = self.create_sales_order()
		so2 = self.create_sales_order()

		pe = self.create_payment_entry()
		# Allocation payment against Sales Order
		pe.paid_amount = 260
		pe.append(
			"references",
			{"reference_doctype": so1.doctype, "reference_name": so1.name, "allocated_amount": 150},
		)
		pe.append(
			"references",
			{"reference_doctype": so2.doctype, "reference_name": so2.name, "allocated_amount": 110},
		)
		pe.save().submit()

		# Assert 'Advance Paid'
		so1.reload()
		self.assertEqual(so1.advance_paid, 150)
		so2.reload()
		self.assertEqual(so2.advance_paid, 110)

		unreconcile = frappe.get_doc(
			{
				"doctype": "Unreconcile Payment",
				"company": self.company,
				"voucher_type": pe.doctype,
				"voucher_no": pe.name,
			}
		)
		unreconcile.add_references()
		self.assertEqual(len(unreconcile.allocations), 2)
		allocations = [(x.reference_name, x.allocated_amount) for x in unreconcile.allocations]
		self.assertListEqual(allocations, [(so1.name, 150), (so2.name, 110)])
		# unreconcile so2
		unreconcile.remove(unreconcile.allocations[0])
		unreconcile.save().submit()

		# Assert 'Advance Paid'
		so1.reload()
		so2.reload()
		pe.reload()
		self.assertEqual(so1.advance_paid, 150)
		self.assertEqual(so2.advance_paid, 110)
		self.assertEqual(len(pe.references), 1)
		self.assertEqual(pe.unallocated_amount, 110)

		self.disable_advance_as_liability()

	def test_07_adv_from_so_to_invoice(self):
		self.enable_advance_as_liability()
		so = self.create_sales_order()
		pe = self.create_payment_entry()
		pe.paid_amount = 1000
		pe.append(
			"references",
			{"reference_doctype": so.doctype, "reference_name": so.name, "allocated_amount": 1000},
		)
		pe.save().submit()

		# Assert 'Advance Paid'
		so.reload()
		self.assertEqual(so.advance_paid, 1000)

		si = make_sales_invoice(so.name)
		si.insert().submit()

		pr = frappe.get_doc(
			{
				"doctype": "Payment Reconciliation",
				"company": self.company,
				"party_type": "Customer",
				"party": so.customer,
			}
		)
		accounts = get_party_account("Customer", so.customer, so.company, True)
		pr.receivable_payable_account = accounts[0]
		pr.default_advance_account = accounts[1]
		pr.get_unreconciled_entries()
		self.assertEqual(len(pr.get("invoices")), 1)
		self.assertEqual(len(pr.get("payments")), 1)
		invoices = [x.as_dict() for x in pr.get("invoices")]
		payments = [x.as_dict() for x in pr.get("payments")]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		self.assertEqual(len(pr.get("invoices")), 0)
		self.assertEqual(len(pr.get("payments")), 0)

		# Assert 'Advance Paid'
		so.reload()
		self.assertEqual(so.advance_paid, 1000)

		self.disable_advance_as_liability()
