# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
from frappe.utils import flt, add_days, nowdate, add_months
import unittest

test_dependencies = ["Product Bundle"]

class TestQuotation(unittest.TestCase):
	def test_make_sales_order(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()

		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)
		quotation.submit()

		sales_order = make_sales_order(quotation.name)

		self.assertEquals(sales_order.doctype, "Sales Order")
		self.assertEquals(len(sales_order.get("items")), 1)
		self.assertEquals(sales_order.get("items")[0].doctype, "Sales Order Item")
		self.assertEquals(sales_order.get("items")[0].prevdoc_docname, quotation.name)
		self.assertEquals(sales_order.customer, "_Test Customer")

		sales_order.delivery_date = "2014-01-01"
		sales_order.naming_series = "_T-Quotation-"
		sales_order.transaction_date = nowdate()
		sales_order.insert()

	def test_valid_till(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		quotation = frappe.copy_doc(test_records[0])
		quotation.valid_till = add_days(quotation.transaction_date, -1)
		self.assertRaises(frappe.ValidationError, quotation.validate)

		quotation.valid_till = add_days(nowdate(), -1)
		quotation.insert()
		quotation.submit()
		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)

	def test_create_quotation_with_margin(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.selling.doctype.sales_order.sales_order \
			import make_delivery_note, make_sales_invoice

		rate_with_margin = flt((1500*18.75)/100 + 1500)

		test_records[0]['items'][0]['price_list_rate'] = 1500
		test_records[0]['items'][0]['margin_type'] = 'Percentage'
		test_records[0]['items'][0]['margin_rate_or_amount'] = 18.75

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()

		self.assertEquals(quotation.get("items")[0].rate, rate_with_margin)
		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.naming_series = "_T-Quotation-"
		sales_order.transaction_date = "2016-01-01"
		sales_order.delivery_date = "2016-01-02"

		sales_order.insert()

		self.assertEquals(quotation.get("items")[0].rate, rate_with_margin)

		sales_order.submit()

		dn = make_delivery_note(sales_order.name)
		self.assertEquals(quotation.get("items")[0].rate, rate_with_margin)
		dn.save()

		si = make_sales_invoice(sales_order.name)
		self.assertEquals(quotation.get("items")[0].rate, rate_with_margin)
		si.save()

test_records = frappe.get_test_records('Quotation')

def get_quotation_dict(customer=None, item_code=None):
	if not customer:
		customer = '_Test Customer'
	if not item_code:
		item_code = '_Test Item'

	return {
		'doctype': 'Quotation',
		'customer': customer,
		'items': [
			{
				'item_code': item_code,
				'qty': 1,
				'rate': 100
			}
		]
	}
