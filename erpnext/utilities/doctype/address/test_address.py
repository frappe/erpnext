# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
test_records = frappe.get_test_records('Address')

import unittest
import frappe

from erpnext.utilities.doctype.address.address import get_address_display

class TestAddress(unittest.TestCase):
	def test_template_works(self):
		address = frappe.get_list("Address")[0].name
		display = get_address_display(frappe.get_doc("Address", address).as_dict())
		self.assertTrue(display)


test_dependencies = ["Address Template"]
