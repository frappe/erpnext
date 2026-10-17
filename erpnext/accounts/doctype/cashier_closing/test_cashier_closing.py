# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.utils import ERPNextTestSuite

DATE = "2026-06-15"


class TestCashierClosing(ERPNextTestSuite):
	"""Cashier Closing reconciles a shift: it pulls outstanding invoices in a
	date/time window and rolls payments, expense, custody and returns into net_amount."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_invoice_in_window(self, rate=100):
		si = create_sales_invoice(rate=rate, qty=1, posting_date=DATE, do_not_submit=True)
		si.posting_time = "10:30:00"
		si.submit()
		si.reload()  # read outstanding_amount as persisted after submit
		return si

	def make_closing(self, user="Administrator", payments=None, **args):
		doc = frappe.new_doc("Cashier Closing")
		doc.user = user
		doc.date = args.get("date", DATE)
		doc.from_time = args.get("from_time", "09:00:00")
		doc.time = args.get("time", "18:00:00")
		for amount in payments or []:
			doc.append("payments", {"mode_of_payment": "Cash", "amount": amount})
		doc.expense = args.get("expense", 0)
		doc.custody = args.get("custody", 0)
		doc.returns = args.get("returns", 0)
		return doc

	def test_equal_from_and_to_time_is_rejected(self):
		# validate_time uses >=, so a zero-length window is also blocked
		doc = self.make_closing(from_time="09:00:00", time="09:00:00")
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_net_amount_rolls_up_outstanding_and_adjustments(self):
		si = self.make_invoice_in_window(rate=100)
		doc = self.make_closing(payments=[500], expense=50, custody=30, returns=20)
		doc.save()

		# the in-window invoice is picked up as outstanding
		self.assertEqual(doc.outstanding_amount, si.outstanding_amount)
		# net = payments + outstanding + expense - custody + returns
		self.assertEqual(doc.net_amount, 500 + si.outstanding_amount + 50 - 30 + 20)

		doc = self.make_closing(user="Guest", payments=[500])
		doc.save()
		self.assertEqual(doc.outstanding_amount, 0)
		self.assertEqual(doc.net_amount, 500)
