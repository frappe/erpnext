# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

test_records = [
	[{"doctype":"Lead", "lead_name": "_Test Lead", "status":"Open", 
		"email_id":"test_lead@example.com", "territory": "_Test Territory"}],
	[{"doctype":"Lead", "lead_name": "_Test Lead 1", "status":"Open", 
		"email_id":"test_lead1@example.com"}],
	[{"doctype":"Lead", "lead_name": "_Test Lead 2", "status":"Contacted", 
		"email_id":"test_lead2@example.com"}],
	[{"doctype":"Lead", "lead_name": "_Test Lead 3", "status":"Converted", 
		"email_id":"test_lead3@example.com"}],
]

import webnotes
import unittest

class TestLead(unittest.TestCase):
	def test_make_customer(self):
		from selling.doctype.lead.lead import make_customer

		customer = make_customer("_T-Lead-00001")
		self.assertEquals(customer[0]["doctype"], "Customer")
		self.assertEquals(customer[0]["lead_name"], "_T-Lead-00001")
		
		customer[0].customer_group = "_Test Customer Group"
		webnotes.bean(customer).insert()
		