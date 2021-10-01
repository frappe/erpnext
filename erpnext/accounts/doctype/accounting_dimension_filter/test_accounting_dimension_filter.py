# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from erpnext.accounts.doctype.accounting_dimension.test_accounting_dimension import (
	create_dimension,
	disable_dimension,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.exceptions import InvalidAccountDimensionError, MandatoryAccountDimensionError

test_dependencies = ['Location', 'Cost Center', 'Department']

class TestAccountingDimensionFilter(unittest.TestCase):
	def setUp(self):
		create_dimension()
		create_accounting_dimension_filter()
		self.invoice_list = []

	def test_allowed_dimension_validation(self):
		si = create_sales_invoice(do_not_save=1)
		si.items[0].cost_center = 'Main - _TC'
		si.department = 'Accounts - _TC'
		si.location = 'Block 1'
		si.save()

		self.assertRaises(InvalidAccountDimensionError, si.submit)
		self.invoice_list.append(si)

	def test_mandatory_dimension_validation(self):
		si = create_sales_invoice(do_not_save=1)
		si.department = ''
		si.location = 'Block 1'

		# Test with no department for Sales Account
		si.items[0].department = ''
		si.items[0].cost_center = '_Test Cost Center 2 - _TC'
		si.save()

		self.assertRaises(MandatoryAccountDimensionError, si.submit)
		self.invoice_list.append(si)

	def tearDown(self):
		disable_dimension_filter()
		disable_dimension()

		for si in self.invoice_list:
			si.load_from_db()
			if si.docstatus == 1:
				si.cancel()

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
		{'accounting_dimension': 'Department'}):
		frappe.get_doc({
			'doctype': 'Accounting Dimension Filter',
			'accounting_dimension': 'Department',
			'allow_or_restrict': 'Allow',
			'company': '_Test Company',
			'accounts': [{
				'applicable_on_account': 'Sales - _TC',
				'is_mandatory': 1
			}],
			'dimensions': [{
				'accounting_dimension': 'Department',
				'dimension_value': 'Accounts - _TC'
			}]
		}).insert()
	else:
		doc = frappe.get_doc('Accounting Dimension Filter', {'accounting_dimension': 'Department'})
		doc.disabled = 0
		doc.save()

def disable_dimension_filter():
	doc = frappe.get_doc('Accounting Dimension Filter', {'accounting_dimension': 'Cost Center'})
	doc.disabled = 1
	doc.save()

	doc = frappe.get_doc('Accounting Dimension Filter', {'accounting_dimension': 'Department'})
	doc.disabled = 1
	doc.save()
