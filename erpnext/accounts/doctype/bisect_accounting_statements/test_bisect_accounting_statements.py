# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBisectAccountingStatements(FrappeTestCase):
	def test_cached_node_preserves_statement_summaries(self):
		doc = frappe.new_doc("Bisect Accounting Statements")
		doc.current_node = frappe.new_doc("Bisect Nodes").insert().name
		doc.p_l_summary = 1200
		doc.b_s_summary = 900
		doc.difference = 300
		doc.update_node()

		doc.p_l_summary = 0
		doc.b_s_summary = 0
		doc.difference = 0
		doc.fetch_or_calculate()

		self.assertEqual(doc.p_l_summary, 1200)
		self.assertEqual(doc.b_s_summary, 900)
		self.assertEqual(doc.difference, 300)
