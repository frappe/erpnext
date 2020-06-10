# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from erpnext.templates.pages.rfq import check_supplier_has_docname_access
from frappe.utils import nowdate

class TestRequestforQuotation(unittest.TestCase):
	def test_quote_status(self):
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import make_supplier_quotation
		rfq = make_request_for_quotation()

		self.assertEqual(rfq.get('suppliers')[0].quote_status, 'Pending')
		self.assertEqual(rfq.get('suppliers')[1].quote_status, 'Pending')

		# Submit the first supplier quotation
		sq = make_supplier_quotation(rfq.name, rfq.get('suppliers')[0].supplier)
		sq.submit()

		# No Quote first supplier quotation
		rfq.get('suppliers')[1].no_quote = 1
		rfq.get('suppliers')[1].quote_status = 'No Quote'

		rfq.update_rfq_supplier_status() #rfq.get('suppliers')[1].supplier)

		self.assertEqual(rfq.get('suppliers')[0].quote_status, 'Received')
		self.assertEqual(rfq.get('suppliers')[1].quote_status, 'No Quote')

	def test_make_supplier_quotation(self):
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import make_supplier_quotation
		rfq = make_request_for_quotation()

		sq = make_supplier_quotation(rfq.name, rfq.get('suppliers')[0].supplier)
		sq.submit()

		sq1 = make_supplier_quotation(rfq.name, rfq.get('suppliers')[1].supplier)
		sq1.submit()

		self.assertEqual(sq.supplier, rfq.get('suppliers')[0].supplier)
		self.assertEqual(sq.get('items')[0].request_for_quotation, rfq.name)
		self.assertEqual(sq.get('items')[0].item_code, "_Test Item")
		self.assertEqual(sq.get('items')[0].qty, 5)

		self.assertEqual(sq1.supplier, rfq.get('suppliers')[1].supplier)
		self.assertEqual(sq1.get('items')[0].request_for_quotation, rfq.name)
		self.assertEqual(sq1.get('items')[0].item_code, "_Test Item")
		self.assertEqual(sq1.get('items')[0].qty, 5)

	def test_make_supplier_quotation_with_special_characters(self):
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import make_supplier_quotation

		frappe.delete_doc_if_exists("Supplier", "_Test Supplier '1", force=1)
		supplier = frappe.new_doc("Supplier")
		supplier.supplier_name = "_Test Supplier '1"
		supplier.supplier_group = "_Test Supplier Group"
		supplier.insert()

		rfq = make_request_for_quotation(supplier_wt_appos)

		sq = make_supplier_quotation(rfq.name, supplier_wt_appos[0].get("supplier"))
		sq.submit()

		frappe.form_dict = frappe.local("form_dict")
		frappe.form_dict.name = rfq.name

		self.assertEqual(
			check_supplier_has_docname_access(supplier_wt_appos[0].get('supplier')),
			True
		)

		# reset form_dict
		frappe.form_dict.name = None

	def test_make_supplier_quotation_from_portal(self):
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import create_supplier_quotation
		rfq = make_request_for_quotation()
		rfq.get('items')[0].rate = 100
		rfq.supplier = rfq.suppliers[0].supplier
		supplier_quotation_name = create_supplier_quotation(rfq)

		supplier_quotation_doc = frappe.get_doc('Supplier Quotation', supplier_quotation_name)

		self.assertEqual(supplier_quotation_doc.supplier, rfq.get('suppliers')[0].supplier)
		self.assertEqual(supplier_quotation_doc.get('items')[0].request_for_quotation, rfq.name)
		self.assertEqual(supplier_quotation_doc.get('items')[0].item_code, "_Test Item")
		self.assertEqual(supplier_quotation_doc.get('items')[0].qty, 5)
		self.assertEqual(supplier_quotation_doc.get('items')[0].amount, 500)


def make_request_for_quotation(supplier_data=None):
	"""
	:param supplier_data: List containing supplier data
	"""
	supplier_data = supplier_data if supplier_data else get_supplier_data()
	rfq = frappe.new_doc('Request for Quotation')
	rfq.transaction_date = nowdate()
	rfq.status = 'Draft'
	rfq.company = '_Test Company'
	rfq.message_for_supplier = 'Please supply the specified items at the best possible rates.'

	for data in supplier_data:
		rfq.append('suppliers', data)

	rfq.append("items", {
		"item_code": "_Test Item",
		"description": "_Test Item",
		"uom": "_Test UOM",
		"qty": 5,
		"warehouse": "_Test Warehouse - _TC",
		"schedule_date": nowdate()
	})

	rfq.submit()

	return rfq

def get_supplier_data():
	return [{
		"supplier": "_Test Supplier",
		"supplier_name": "_Test Supplier"
	},
	{
		"supplier": "_Test Supplier 1",
		"supplier_name": "_Test Supplier 1"
	}]

supplier_wt_appos = [{
	"supplier": "_Test Supplier '1",
	"supplier_name": "_Test Supplier '1",
}]
