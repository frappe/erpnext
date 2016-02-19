# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe import _
# test_records = frappe.get_test_records('Translation')

class TestTranslation(unittest.TestCase):
	def test_doctype(self):
		translation_data = {'hr': ['Test data', 'Testdaten'], 'ms':['Test Data','ujian Data'],
							'et':['Test Data', 'testandmed']}
		for key, val in translation_data.items():
			frappe.local.lang = key
			frappe.local.lang_full_dict=None
			translation = create_translation(key, val)
			self.assertEquals(_(translation.source_name), val[1])
			frappe.delete_doc('Translation', translation.name)

def create_translation(key, val):
	translation = frappe.new_doc('Translation')
	translation.language_code = key
	translation.source_name = val[0]
	translation.target_name = val[1]
	translation.save()
	return translation
