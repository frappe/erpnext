# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes
import unittest

class TestCustomer(unittest.TestCase):
	def test_rename(self):
		self.assertEqual(webnotes.conn.exists("Customer", "_Test Customer 1"), 
			(("_Test Customer 1",),))
			
		webnotes.rename_doc("Customer", "_Test Customer 1", "_Test Customer 1 Renamed")

		self.assertEqual(webnotes.conn.exists("Customer", "_Test Customer 1 Renamed"), 
			(("_Test Customer 1 Renamed",),))
		self.assertEqual(webnotes.conn.exists("Customer", "_Test Customer 1"), ())
		
		webnotes.rename_doc("Customer", "_Test Customer 1 Renamed", "_Test Customer 1")
		
	def test_merge(self):
		from webnotes.test_runner import make_test_records
		make_test_records("Sales Invoice")
		
		# clear transactions for new name
		webnotes.conn.sql("""delete from `tabSales Invoice` where customer='_Test Customer 1'""")
		
		# check if they exist
		self.assertEqual(webnotes.conn.exists("Customer", "_Test Customer"), 
			(("_Test Customer",),))
		self.assertEqual(webnotes.conn.exists("Customer", "_Test Customer 1"), 
			(("_Test Customer 1",),))
		self.assertEqual(webnotes.conn.exists("Account", "_Test Customer - _TC"), 
			(("_Test Customer - _TC",),))
		self.assertEqual(webnotes.conn.exists("Account", "_Test Customer 1 - _TC"), 
			(("_Test Customer 1 - _TC",),))
			
		# check if transactions exists
		self.assertNotEquals(webnotes.conn.sql("""select count(*) from `tabSales Invoice` 
			where customer='_Test Customer'""", )[0][0], 0)
		self.assertNotEquals(webnotes.conn.sql("""select count(*) from `tabSales Invoice` 
			where debit_to='_Test Customer - _TC'""", )[0][0], 0)
		
		webnotes.rename_doc("Customer", "_Test Customer", "_Test Customer 1", merge=True)
		
		# check that no transaction exists for old name
		self.assertNotEquals(webnotes.conn.sql("""select count(*) from `tabSales Invoice` 
			where customer='_Test Customer 1'""", )[0][0], 0)
		self.assertNotEquals(webnotes.conn.sql("""select count(*) from `tabSales Invoice` 
			where debit_to='_Test Customer 1 - _TC'""", )[0][0], 0)
		
		# check that transactions exist for new name
		self.assertEquals(webnotes.conn.sql("""select count(*) from `tabSales Invoice` 
			where customer='_Test Customer'""", )[0][0], 0)
		self.assertEquals(webnotes.conn.sql("""select count(*) from `tabSales Invoice` 
			where debit_to='_Test Customer - _TC'""", )[0][0], 0)
			
		# check that old name doesn't exist
		self.assertEqual(webnotes.conn.exists("Customer", "_Test Customer"), ())
		self.assertEqual(webnotes.conn.exists("Account", "_Test Customer - _TC"), ())
		
		# create back _Test Customer
		webnotes.bean(copy=test_records[0]).insert()

test_ignore = ["Price List"]
			
test_records = [
	[{
		"doctype": "Customer",
		"customer_name": "_Test Customer",
		"customer_type": "Individual",
		"customer_group": "_Test Customer Group",
		"territory": "_Test Territory",
		"company": "_Test Company"
	}],
	[{
		"doctype": "Customer",
		"customer_name": "_Test Customer 1",
		"customer_type": "Individual",
		"customer_group": "_Test Customer Group",
		"territory": "_Test Territory",
		"company": "_Test Company"
	}]
]