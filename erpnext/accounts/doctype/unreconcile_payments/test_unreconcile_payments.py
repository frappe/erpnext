# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestUnreconcilePayments(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def test_01_unreconcile_invoice(self):
		si1 = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			price_list_rate=100,
		)

		si2 = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			price_list_rate=100,
		)

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
		si1.reload()
		si2.reload()
		self.assertEqual(si1.outstanding_amount, 0)
		self.assertEqual(si2.outstanding_amount, 0)

		unreconcile = frappe.get_doc(
			{
				"doctype": "Unreconcile Payments",
				"company": self.company,
				"voucher_type": pe.doctype,
				"voucher_no": pe.name,
			}
		)
		unreconcile.add_references()
		self.assertEqual(len(unreconcile.allocations), 2)
		allocations = [x.reference_name for x in unreconcile.allocations]
		self.assertEquals([si1.name, si2.name], allocations)
		# unreconcile si1
		for x in unreconcile.allocations:
			if x.reference_name != si1.name:
				unreconcile.remove(x)
		unreconcile.save().submit()

		# Assert outstanding
		si1.reload()
		si2.reload()
		self.assertEqual(si1.outstanding_amount, 100)
		self.assertEqual(si2.outstanding_amount, 0)

		pe.reload()
		self.assertEqual(len(pe.references), 1)
