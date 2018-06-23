# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_dependencies = ["Customer", "Supplier"]
from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import get_temporary_opening_account

class TestOpeningInvoiceCreationTool(unittest.TestCase):
	def make_invoices(self, invoice_type="Sales"):
		doc = frappe.get_single("Opening Invoice Creation Tool")
		args = get_opening_invoice_creation_dict(invoice_type=invoice_type)
		doc.update(args)
		return doc.make_invoices()

	def test_opening_sales_invoice_creation(self):
		invoices = self.make_invoices()

		self.assertEqual(len(invoices), 2)
		expected_value = {
			"keys": ["customer", "outstanding_amount", "status"],
			0: ["_Test Customer", 300, "Overdue"],
			1: ["_Test Customer 1", 250, "Overdue"],
		}
		self.check_expected_values(invoices, expected_value)

	def check_expected_values(self, invoices, expected_value, invoice_type="Sales"):
		doctype = "Sales Invoice" if invoice_type == "Sales" else "Purchase Invoice"

		for invoice_idx, invoice in enumerate(invoices or []):
			si = frappe.get_doc(doctype, invoice)
			for field_idx, field in enumerate(expected_value["keys"]):
				self.assertEqual(si.get(field, ""), expected_value[invoice_idx][field_idx])

	def test_opening_purchase_invoice_creation(self):
		invoices = self.make_invoices(invoice_type="Purchase")

		self.assertEqual(len(invoices), 2)
		expected_value = {
			"keys": ["supplier", "outstanding_amount", "status"],
			0: ["_Test Supplier", 300, "Overdue"],
			1: ["_Test Supplier 1", 250, "Overdue"],
		}
		self.check_expected_values(invoices, expected_value, invoice_type="Purchase", )

def get_opening_invoice_creation_dict(**args):
	party = "Customer" if args.get("invoice_type", "Sales") == "Sales" else "Supplier"
	company = args.get("company", "_Test Company")

	invoice_dict = frappe._dict({
		"company": company,
		"invoice_type": args.get("invoice_type", "Sales"),
		"invoices": [
			{
				"qty": 1.0,
				"outstanding_amount": 300,
				"party": "_Test {0}".format(party),
				"item_name": "Opening Item",
				"due_date": "2016-09-10",
				"posting_date": "2016-09-05",
				"temporary_opening_account": get_temporary_opening_account(company)
			},
			{
				"qty": 2.0,
				"outstanding_amount": 250,
				"party": "_Test {0} 1".format(party),
				"item_name": "Opening Item",
				"due_date": "2016-09-10",
				"posting_date": "2016-09-05",
				"temporary_opening_account": get_temporary_opening_account(company)
			}
		]
	})

	invoice_dict.update(args)
	return invoice_dict