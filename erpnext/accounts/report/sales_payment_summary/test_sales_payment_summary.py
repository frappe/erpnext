# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
from erpnext.accounts.report.sales_payment_summary.sales_payment_summary import get_mode_of_payments, get_mode_of_payment_details
from frappe.utils import nowdate
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

test_dependencies = ["Sales Invoice"]

class TestSalesPaymentSummary(unittest.TestCase):
	def setUp(self):
		pass

	def tearDown(self):
		pass

	def test_get_mode_of_payments(self):
		si = frappe.get_all("Sales Invoice", filters={"company": "_Test Company", "customer": "_Test Customer"}, fields=["name", "docstatus"])
		filters = get_filters()

		for invoice in si[:-2]:
			doc = frappe.get_doc("Sales Invoice", invoice.name)
			new_doc = frappe.copy_doc(doc)
			new_doc.ignore_pricing_rule = 1
			for item in new_doc.items:
				item.pricing_rule = ""
			new_doc.insert()
			new_doc.submit()
			try:
				new_doc.submit()
			except Exception as e:
				print(e)

			if int(new_doc.name[-3:])%2 == 0:
				bank_account = "_Test Cash - _TC"
				mode_of_payment = "Cash"
			else:
				bank_account = "_Test Bank - _TC"
				mode_of_payment = "Credit Card"

			pe = get_payment_entry("Sales Invoice", new_doc.name, bank_account=bank_account)
			pe.reference_no = "_Test"
			pe.reference_date = nowdate()
			pe.mode_of_payment = mode_of_payment
			pe.insert()
			pe.submit()

		mop = get_mode_of_payments(filters)
		self.assertTrue('Credit Card' in mop.values()[0])
		self.assertTrue('Cash' in mop.values()[0])

		# Cancel all Cash payment entry and check if this mode of payment is still fetched.
		payment_entries = frappe.get_all("Payment Entry", filters={"mode_of_payment": "Cash", "docstatus": 1}, fields=["name", "docstatus"])
		for payment_entry in payment_entries:
			pe = frappe.get_doc("Payment Entry", payment_entry.name)
			pe.cancel()

		mop = get_mode_of_payments(filters)
		self.assertTrue('Credit Card' in mop.values()[0])
		self.assertTrue('Cash' not in mop.values()[0])

	def test_get_mode_of_payments_details(self):
		si = frappe.get_all("Sales Invoice", filters={"company": "_Test Company", "customer": "_Test Customer"}, fields=["name", "docstatus"])
		filters = get_filters()

		for invoice in si[:-2]:
			doc = frappe.get_doc("Sales Invoice", invoice.name)
			new_doc = frappe.copy_doc(doc)
			new_doc.ignore_pricing_rule = 1
			for item in new_doc.items:
				item.pricing_rule = ""
			new_doc.insert()
			new_doc.submit()
			try:
				new_doc.submit()
			except Exception as e:
				print(e)

			if int(new_doc.name[-3:])%2 == 0:
				bank_account = "_Test Cash - _TC"
				mode_of_payment = "Cash"
			else:
				bank_account = "_Test Bank - _TC"
				mode_of_payment = "Credit Card"

			pe = get_payment_entry("Sales Invoice", new_doc.name, bank_account=bank_account)
			pe.reference_no = "_Test"
			pe.reference_date = nowdate()
			pe.mode_of_payment = mode_of_payment
			pe.insert()
			pe.submit()

		mopd = get_mode_of_payment_details(filters)

		mopd_values = mopd.values()[0]
		for mopd_value in mopd_values:
			if mopd_value[0] == "Credit Card":
				cc_init_amount = mopd_value[1]

		# Cancel one Credit Card Payment Entry and check that it is not fetched in mode of payment details.
		payment_entries = frappe.get_all("Payment Entry", filters={"mode_of_payment": "Credit Card", "docstatus": 1}, fields=["name", "docstatus"])
		for payment_entry in payment_entries[:1]:
			pe = frappe.get_doc("Payment Entry", payment_entry.name)
			pe.cancel()

		mopd = get_mode_of_payment_details(filters)
		mopd_values = mopd.values()[0]
		for mopd_value in mopd_values:
			if mopd_value[0] == "Credit Card":
				cc_final_amount = mopd_value[1]

		self.assertTrue(cc_init_amount > cc_final_amount)

def get_filters():
	return {
		"from_date": "1900-01-01",
		"to_date": nowdate(),
		"company": "_Test Company"
	}