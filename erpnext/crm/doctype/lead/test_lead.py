# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import unittest

test_records = frappe.get_test_records('Lead')

class TestLead(unittest.TestCase):
	def test_make_customer(self):
		from erpnext.crm.doctype.lead.lead import make_customer

		frappe.delete_doc_if_exists("Customer", "_Test Lead")

		customer = make_customer("_T-Lead-00001")
		self.assertEquals(customer.doctype, "Customer")
		self.assertEquals(customer.lead_name, "_T-Lead-00001")

		customer.company = "_Test Company"
		customer.customer_group = "_Test Customer Group"
		customer.insert()

	def test_make_customer_from_organization(self):
		from erpnext.crm.doctype.lead.lead import make_customer

		customer = make_customer("_T-Lead-00002")
		self.assertEquals(customer.doctype, "Customer")
		self.assertEquals(customer.lead_name, "_T-Lead-00002")

		customer.company = "_Test Company"
		customer.customer_group = "_Test Customer Group"
		customer.insert()
