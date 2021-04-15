# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestTransactionDeletionLog(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_no_of_docs(self):
		for i in range(5):
			create_todo('Pied Piper')
		tdr = create_transaction_deletion_request('Pied Piper')
		for doctype in tdr.doctypes:
			if doctype.doctype_name == 'ToDo':
				self.assertEqual(doctype.no_of_docs, 5)

	def test_doctypes_contain_company_field(self):
		tdr = create_transaction_deletion_request('Pied Piper')
		for doctype in tdr.doctypes:
			flag = False
			doctype_fields = frappe.get_meta(doctype.doctype_name).as_dict()['fields']
			for doctype_field in doctype_fields:
				if doctype_field['fieldtype'] == 'Link' and doctype_field['options'] == 'Company':
					flag = True
					break
			self.assertTrue(flag)

def create_transaction_deletion_request(company):
	tdr = frappe.get_doc({
		'doctype': 'Transaction Deletion Log',
		'company': company
	})
	tdr.insert()
	return tdr


def create_todo(company):
	todo = frappe.get_doc({
		'doctype': 'ToDo',
		'company': company,
		'description': 'Delete'
	})
	todo.insert()