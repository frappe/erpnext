# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and Contributors
# See license.txt
from __future__ import unicode_literals
import unittest
import frappe

test_dependencies = ['Physician Schedule']


class TestPhysician(unittest.TestCase):
	def tearDown(self):
		frappe.delete_doc_if_exists('Physician', '_Testdoctor2', force=1)

	def test_new_physician_without_schedule(self):
		physician = frappe.new_doc('Physician')
		physician.first_name = '_Testdoctor2'

		physician.insert()
		self.assertEqual(frappe.get_value('Physician', '_Testdoctor2', 'first_name'), '_Testdoctor2')
