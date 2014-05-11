# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes, unittest

test_dependencies = ["Item"]
test_records = []

from stock.doctype.serial_no.serial_no import *

class TestSerialNo(unittest.TestCase):
	def test_cannot_create_direct(self):
		sr = webnotes.new_bean("Serial No")
		sr.doc.item_code = "_Test Serialized Item"
		sr.doc.warehouse = "_Test Warehouse - _TC"
		sr.doc.serial_no = "_TCSER0001"
		sr.doc.purchase_rate = 10
		self.assertRaises(SerialNoCannotCreateDirectError, sr.insert)
		
		sr.doc.warehouse = None
		sr.insert()
		self.assertTrue(sr.doc.name)

		sr.doc.warehouse = "_Test Warehouse - _TC"
		self.assertTrue(SerialNoCannotCannotChangeError, sr.doc.save)