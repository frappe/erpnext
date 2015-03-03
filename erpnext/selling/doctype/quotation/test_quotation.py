# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe, json
from frappe.utils import flt
import unittest

test_dependencies = ["Sales BOM"]

class TestQuotation(unittest.TestCase):
	def test_make_sales_order(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		quotation = frappe.copy_doc(test_records[0])
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
		sales_order.transaction_date = "2013-05-12"
		sales_order.insert()


test_records = frappe.get_test_records('Quotation')
