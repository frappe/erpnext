# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import cint
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from frappe.model.naming import parse_naming_series

class TestNamingSeries(unittest.TestCase):
	def test_naming_series(self):
		naming_series = "SINV-"
		current = frappe.db.get_value("Series", naming_series, "current", order_by = "name") or 0

		si = create_sales_invoice(qty=100, rate=50, do_not_submit=True, naming_series=naming_series)
		self.assertEquals(cint(current + 1), frappe.db.get_value("Series", naming_series, "current", order_by = "name"))

		frappe.delete_doc('Sales Invoice', si.name)
		self.assertEquals(cint(current), frappe.db.get_value("Series", naming_series, "current", order_by = "name"))

	def test_naming_series_with_multiple_dot(self):
		naming_series = "INV/17-18/.test_data./.####"
		prefix = "INV/17-18/.test_data./"
		prefix = parse_naming_series(prefix.split("."))

		add_naming_series(doctype="Sales Invoice", options=naming_series)
		current = frappe.db.get_value("Series", prefix, "current", order_by = "name") or 0

		si = create_sales_invoice(qty=100, rate=50, do_not_submit=True, naming_series=naming_series)
		self.assertEquals(cint(current + 1), frappe.db.get_value("Series", prefix, "current", order_by = "name"))

		frappe.delete_doc('Sales Invoice', si.name)
		self.assertEquals(cint(current), frappe.db.get_value("Series", prefix, "current", order_by = "name"))

	def test_naming_series_with_date_format(self):
		naming_series = 'INV.YYYY.MM.#####'
		prefix = "INV.YYYY.MM"
		prefix = parse_naming_series(prefix.split("."))

		add_naming_series(doctype="Sales Invoice", options=naming_series)

		current = frappe.db.get_value("Series", prefix, "current", order_by = "name") or 0
		si = create_sales_invoice(qty=100, rate=50, do_not_submit=True, naming_series=naming_series)
		self.assertEquals(cint(current + 1), frappe.db.get_value("Series", prefix, "current", order_by = "name"))

		frappe.delete_doc('Sales Invoice', si.name)
		self.assertEquals(cint(current), frappe.db.get_value("Series", prefix, "current", order_by = "name"))

def add_naming_series(**args):
	args = frappe._dict(args)

	doc = frappe.get_doc({'doctype': 'Naming Series'})
	doc.select_doc_for_series = args.doctype
	if args.doctype and not args.options:
		options = frappe.get_meta(args.doctype).get_field("naming_series").options or "SINV-"

	doc.set_options = args.options or options
	doc.update_series()