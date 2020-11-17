# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.accounting_dimension.test_accounting_dimension import create_dimension

class TestAccountingDimensionFilter(unittest.TestCase):
	def setUp(self):
		create_dimension()
		create_accounting_dimension_filter()

	def test_allowed_dimension_validation(self):
		si = create_sales_invoice(do_not_save=1)
		si.items[0].cost_center = 'Main - _TC'
		si.save()

		self.assertRaises(frappe.ValidationError, si.submit)

	def test_mandatory_dimension_validation(self):
		si = create_sales_invoice(do_not_save=1)
		si.items[0].location = ''
		si.save()

		self.assertRaises(frappe.ValidationError, si.submit)

	def tearDown(self):
		disable_dimension_filter()

def create_accounting_dimension_filter():
	if not frappe.db.get_value('Accounting Dimension Filter',
		{'accounting_dimension': 'Cost Center'}):
		frappe.get_doc({
			'doctype': 'Accounting Dimension Filter',
			'accounting_dimension': 'Cost Center',
			'allow_or_restrict': 'Allow',
			'company': '_Test Company',
			'accounts': [{
				'applicable_on_account': 'Sales - _TC',
			}],
			'dimensions': [{
				'accounting_dimension': 'Cost Center',
				'dimension_value': '_Test Cost Center 2 - _TC'
			}]
		}).insert()
	else:
		doc = frappe.get_doc('Accounting Dimension Filter', {'accounting_dimension': 'Cost Center'})
		doc.disabled = 0
		doc.save()

	if not frappe.db.get_value('Accounting Dimension Filter',
		{'accounting_dimension': 'Location'}):
		frappe.get_doc({
			'doctype': 'Accounting Dimension Filter',
			'accounting_dimension': 'Location',
			'allow_or_restrict': 'Allow',
			'company': '_Test Company',
			'accounts': [{
				'applicable_on_account': 'Sales - _TC',
				'is_mandatory': 1
			}],
			'dimensions': [{
				'accounting_dimension': 'Location',
				'dimension_value': 'Block 1'
			}]
		}).insert()
	else:
		doc = frappe.get_doc('Accounting Dimension Filter', {'accounting_dimension': 'Location'})
		doc.disabled = 0
		doc.save()

def disable_dimension_filter():
	doc = frappe.get_doc('Accounting Dimension Filter', {'accounting_dimension': 'Cost Center'})
	doc.disabled = 1
	doc.save()

	doc = frappe.get_doc('Accounting Dimension Filter', {'accounting_dimension': 'Location'})
	doc.disabled = 1
	doc.save()
