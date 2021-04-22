# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestTransactionDeletionTest(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_doctypes_contain_company_field(self):
		tdr = create_transaction_deletion_request('Pied Piper')
		for doctype in tdr.doctypes:
			contains_company = False
			doctype_fields = frappe.get_meta(doctype.doctype_name).as_dict()['fields']
			for doctype_field in doctype_fields:
				if doctype_field['fieldtype'] == 'Link' and doctype_field['options'] == 'Company':
					contains_company = True
					break
			self.assertTrue(contains_company)
	
	def test_no_of_docs_is_correct(self):
		for i in range(5):
			create_task('Pied Piper')
		tdr = create_transaction_deletion_request('Pied Piper')
		for doctype in tdr.doctypes:
			if doctype.doctype_name == 'Task':
				self.assertEqual(doctype.no_of_docs, 5)

	def test_deletion_is_successful(self):
		create_task('Pied Piper')
		create_transaction_deletion_request('Pied Piper')
		tasks_containing_company = frappe.get_all('Task',
		filters = {
			'company' : 'Pied Piper'
		})
		self.assertEqual(tasks_containing_company, [])
		
		
def create_transaction_deletion_request(company):
	tdr = frappe.get_doc({
		'doctype': 'Transaction Deletion Tool',
		'company': company
	})
	tdr.insert()
	tdr.before_submit()
	return tdr


def create_task(company):
	task = frappe.get_doc({
		'doctype': 'Task',
		'company': company,
		'subject': 'Delete'
	})
	task.insert()