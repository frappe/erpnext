# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.report.sales_payment_summary.sales_payment_summary import (
	get_mode_of_payment_details,
	get_mode_of_payments,
)

EXTRA_TEST_RECORD_DEPENDENCIES = ["Sales Invoice"]


class TestSalesPaymentSummary(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_records()
		pes = frappe.get_all("Payment Entry")
		jes = frappe.get_all("Journal Entry")
		sis = frappe.get_all("Sales Invoice")
		for pe in pes:
			frappe.db.set_value("Payment Entry", pe.name, "docstatus", 2)
		for je in jes:
			frappe.db.set_value("Journal Entry", je.name, "docstatus", 2)
		for si in sis:
			frappe.db.set_value("Sales Invoice", si.name, "docstatus", 2)

	def test_get_mode_of_payments(self):
		filters = get_filters()

		for _dummy in range(2):
			si = create_sales_invoice_record()
			si.insert()
			si.submit()

			if int(si.name[-3:]) % 2 == 0:
				bank_account = "_Test Cash - _TC"
				mode_of_payment = "Cash"
			else:
				bank_account = "_Test Bank - _TC"
				mode_of_payment = "Credit Card"

			pe = get_payment_entry("Sales Invoice", si.name, bank_account=bank_account)
			pe.reference_no = "_Test"
			pe.reference_date = today()
			pe.mode_of_payment = mode_of_payment
			pe.insert()
			pe.submit()

		mop = get_mode_of_payments(filters)
		self.assertTrue("Credit Card" in next(iter(mop.values())))
		self.assertTrue("Cash" in next(iter(mop.values())))

		# Cancel all Cash payment entry and check if this mode of payment is still fetched.
		payment_entries = frappe.get_all(
			"Payment Entry",
			filters={"mode_of_payment": "Cash", "docstatus": 1},
			fields=["name", "docstatus"],
		)
		for payment_entry in payment_entries:
			pe = frappe.get_doc("Payment Entry", payment_entry.name)
			pe.cancel()

		mop = get_mode_of_payments(filters)
		self.assertTrue("Credit Card" in next(iter(mop.values())))
		self.assertTrue("Cash" not in next(iter(mop.values())))

	def test_get_mode_of_payments_details(self):
		filters = get_filters()

		for _dummy in range(2):
			si = create_sales_invoice_record()
			si.insert()
			si.submit()

			if int(si.name[-3:]) % 2 == 0:
				bank_account = "_Test Cash - _TC"
				mode_of_payment = "Cash"
			else:
				bank_account = "_Test Bank - _TC"
				mode_of_payment = "Credit Card"

			pe = get_payment_entry("Sales Invoice", si.name, bank_account=bank_account)
			pe.reference_no = "_Test"
			pe.reference_date = today()
			pe.mode_of_payment = mode_of_payment
			pe.insert()
			pe.submit()

		mopd = get_mode_of_payment_details(filters)

		mopd_values = next(iter(mopd.values()))
		for mopd_value in mopd_values:
			if mopd_value[0] == "Credit Card":
				cc_init_amount = mopd_value[1]

		# Cancel one Credit Card Payment Entry and check that it is not fetched in mode of payment details.
		payment_entries = frappe.get_all(
			"Payment Entry",
			filters={"mode_of_payment": "Credit Card", "docstatus": 1},
			fields=["name", "docstatus"],
		)
		for payment_entry in payment_entries[:1]:
			pe = frappe.get_doc("Payment Entry", payment_entry.name)
			pe.cancel()

		mopd = get_mode_of_payment_details(filters)
		mopd_values = next(iter(mopd.values()))
		for mopd_value in mopd_values:
			if mopd_value[0] == "Credit Card":
				cc_final_amount = mopd_value[1]

		self.assertTrue(cc_init_amount > cc_final_amount)


def get_filters():
	return {"from_date": "1900-01-01", "to_date": today(), "company": "_Test Company"}


def create_sales_invoice_record(qty=1):
	# return sales invoice doc object
	return frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": frappe.get_doc("Customer", {"customer_name": "Prestiga-Biz"}).name,
			"company": "_Test Company",
			"due_date": today(),
			"posting_date": today(),
			"currency": "INR",
			"taxes_and_charges": "",
			"debit_to": "Debtors - _TC",
			"taxes": [],
			"items": [
				{
					"doctype": "Sales Invoice Item",
					"item_code": frappe.get_doc("Item", {"item_name": "Consulting"}).name,
					"qty": qty,
					"rate": 10000,
					"income_account": "Sales - _TC",
					"cost_center": "Main - _TC",
					"expense_account": "Cost of Goods Sold - _TC",
				}
			],
		}
	)


def create_records():
	if frappe.db.exists("Customer", "Prestiga-Biz"):
		return

	# customer
	frappe.get_doc(
		{
			"customer_group": "_Test Customer Group",
			"customer_name": "Prestiga-Biz",
			"customer_type": "Company",
			"doctype": "Customer",
			"territory": "_Test Territory",
		}
	).insert()

	# item
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": "Consulting",
			"item_name": "Consulting",
			"item_group": "All Item Groups",
			"company": "_Test Company",
			"is_stock_item": 0,
		}
	).insert()

	# item price
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"price_list": "Standard Selling",
			"item_code": item.item_code,
			"price_list_rate": 10000,
		}
	).insert()
