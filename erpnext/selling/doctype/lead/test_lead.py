# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

test_records = frappe.get_test_records('Lead')

import frappe
import unittest

class TestLead(unittest.TestCase):
	def test_make_customer(self):
		print "test_make_customer"
		from erpnext.selling.doctype.lead.lead import make_customer

		customer = make_customer("_T-Lead-00001")
		self.assertEquals(customer[0]["doctype"], "Customer")
		self.assertEquals(customer[0]["lead_name"], "_T-Lead-00001")
		
		customer[0]["company"] = "_Test Company"
		customer[0]["customer_group"] = "_Test Customer Group"
		frappe.get_doc(customer).insert()