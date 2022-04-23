# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from .quality_procedure import add_node

class TestQualityProcedure(unittest.TestCase):
	def test_add_node(self):
		try:
			procedure = frappe.get_doc(dict(
				doctype = 'Quality Procedure',
				quality_procedure_name = 'Test Procedure 1',
				processes = [
					dict(process_description = 'Test Step 1')
				]
			)).insert()

			frappe.form_dict = dict(doctype = 'Quality Procedure', quality_procedure_name = 'Test Child 1',
				parent_quality_procedure = procedure.name, cmd='test', is_root='false')
			node = add_node()

			procedure.reload()

			self.assertEqual(procedure.is_group, 1)

			# child row created
			self.assertTrue([d for d in procedure.processes if d.procedure == node.name])

			node.delete()
			procedure.reload()

			# child unset
			self.assertFalse([d for d in procedure.processes if d.name == node.name])

		finally:
			procedure.delete()

def create_procedure():
	return frappe.get_doc(dict(
		doctype = 'Quality Procedure',
		quality_procedure_name = 'Test Procedure 1',
		is_group = 1,
		processes = [
			dict(process_description = 'Test Step 1')
		]
	)).insert()