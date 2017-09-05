# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_dependencies = ["Customer", "Supplier"]

class TestOpeningInvoiceCreationTool(unittest.TestCase):
	def make_invoices(self, invoice_type="Sales"):
		invoices = []
		doc = frappe.get_single("Opening Invoice Creation Tool")
		args = get_opening_invoice_creation_dict(invoice_type=invoice_type)
		doc.update(args)
		return doc.make_invoices()

	def test_opening_sales_invoice_creation(self):
		invoices = self.make_invoices()

		self.assertEqual(len(invoices), 3)
		expected_value = {
			"keys": ["customer", "grand_total", "outstanding_amount", "status"],
			0: ["_Test Customer", 300, 75.50, "Overdue"],
			1: ["_Test Customer 1", 250, 45.50, "Overdue"],
			2: ["_Test Customer 2", 150, 0, "Paid"]
		}
		self.check_expected_values(invoices=invoices, expected_value=expected_value)

	def check_expected_values(self, invoice_type="Sales", invoices=[], expected_value={}):
		doctype = "Sales Invoice" if invoice_type == "Sales" else "Purchase Invoice"

		for invoice_idx, invoice in enumerate(invoices):
			si = frappe.get_doc(doctype, invoice)
			for field_idx, field in enumerate(expected_value["keys"]):
				self.assertEqual(si.get(field, ""), expected_value[invoice_idx][field_idx])

	def test_opening_purchase_invoice_creation(self):
		invoices = self.make_invoices(invoice_type="Purchase")

		self.assertEqual(len(invoices), 3)
		expected_value = {
			"keys": ["supplier", "grand_total", "outstanding_amount", "status"],
			0: ["_Test Supplier", 300, 75.50, "Overdue"],
			1: ["_Test Supplier 1", 250, 45.50, "Overdue"],
			2: ["_Test Supplier 2", 150, 0, "Paid"]
		}
		self.check_expected_values(invoice_type="Purchase", invoices=invoices, expected_value=expected_value)

def get_opening_invoice_creation_dict(**args):
	party = "Customer" if args.get("invoice_type", "Sales") == "Sales" else "Supplier"

	invoice_dict = frappe._dict({
		"company": args.get("company", "_Test Company"),
		"invoice_type": args.get("invoice_type", "Sales"),
		"invoices": [
			{
				"qty": 1.0,
				"net_total": 300,
				"outstanding_amount": 75.50,
				"party": "_Test {0}".format(party),
				"item_name": "Opening Item",
				"due_date": "2016-09-10",
				"posting_date": "2016-09-05"
			},
			{
				"qty": 2.0,
				"net_total": 250,
				"outstanding_amount": 45.50,
				"party": "_Test {0} 1".format(party),
				"item_name": "Opening Item",
				"due_date": "2016-09-10",
				"posting_date": "2016-09-05"
			},
			{
				"qty": 2.0,
				"net_total": 150,
				"outstanding_amount": 0,
				"party": "_Test {0} 2".format(party),
				"item_name": "Opening Item",
				"due_date": "2016-09-10",
				"posting_date": "2016-09-05"
			}
		]
	})

	invoice_dict.update(args)
	return invoice_dict