# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWBSBudget(FrappeTestCase):
	def setUp(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		create_company()

	def tearDown(self):
		frappe.db.rollback()

	def test_create_wbs_budget(self):
		doc = frappe.get_doc({
			"doctype": "WBS Budget",
			"company": "_Test Company"
		})
		doc.insert()
		self.assertTrue(doc.name)
		self.assertEqual(doc.company, "_Test Company")

	