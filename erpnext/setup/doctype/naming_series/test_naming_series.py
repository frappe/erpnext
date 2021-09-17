# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import now_datetime

from frappe.model.naming import getseries
from erpnext.setup.doctype.naming_series.naming_series import NamingSeries

class TestNamingSeries(unittest.TestCase):

	def tearDown(self):
		# Reset ToDo autoname to hash
		todo_doctype = frappe.get_doc('DocType', 'ToDo')
		todo_doctype.autoname = 'hash'
		todo_doctype.save()

	def test_series_with_docfields(self):
		doctype = 'ToDo'

		todo_doctype = frappe.get_doc('DocType', doctype)
		row = todo_doctype.append('fields', {
			'fieldname': 'naming_series',
			'fieldtype': 'Select',
			'options': 'TODO-.{status}.-.##',
			'label': 'Series'
		})

		todo_doctype.autoname = 'naming_series:'
		todo_doctype.save()

		description = 'Format'

		todo = frappe.new_doc(doctype)
		todo.description = description
		todo.insert()

		NS = frappe.get_doc('Naming Series')

		prefixes = NS.get_transactions().get('prefixes')
		self.assertIn('TODO-Open-', prefixes)

