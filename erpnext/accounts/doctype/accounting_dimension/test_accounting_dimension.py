# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

class TestAccountingDimension(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")

		if not frappe.db.exists("Accounting Dimension", {"document_type": "Department"}):
			dimension = frappe.get_doc({
				"doctype": "Accounting Dimension",
				"document_type": "Department",
			}).insert()

			dimension1 = frappe.get_doc({
				"doctype": "Accounting Dimension",
				"document_type": "Location",
				"mandatory_for_pl": 1
			}).insert()

	def tearDown(self):
		delete_dimension()

	def test_dimension_against_sales_invoice(self):
		si = create_sales_invoice(do_not_save=1)
		si.append("items", {
			"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC",
			"qty": 1,
			"rate": 100,
			"income_account": "Sales - _TC",
			"expense_account": "Cost of Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"department": "_Test Department - _TC"
		})

		si.save()
		si.submit()

		gle = frappe.get_doc("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"})

		self.assertEqual(gle.department, "_Test Department - _TC")

	def test_dimension_against_journal_entry(self):
		je = make_journal_entry("Sales - _TC", "Sales Expenses - _TC", 500, save=False)
		je.accounts[0].update({"department": "_Test Department - _TC"})
		je.accounts[1].update({"department": "_Test Department - _TC"})

		je.save()
		je.submit()

		gle = frappe.get_doc("GL Entry", {"voucher_no": je.name, "account": "Sales - _TC"})
		gle1 = frappe.get_doc("GL Entry", {"voucher_no": je.name, "account": "Sales Expenses - _TC"})
		self.assertEqual(gle.department, "_Test Department - _TC")
		self.assertEqual(gle1.department, "_Test Department - _TC")

	def test_mandatory(self):
		si = create_sales_invoice(do_not_save=1)
		si.append("items", {
			"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC",
			"qty": 1,
			"rate": 100,
			"income_account": "Sales - _TC",
			"expense_account": "Cost of Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"location": ""
		})

		si.save()
		self.assertRaises(frappe.ValidationError, si.submit())


def delete_dimension():
	dimension1 = frappe.delete_doc("Accounting Diemnsion", "Department")
	dimension2 = frappe.delete_doc("Accounting Diemnsion", "Location")

