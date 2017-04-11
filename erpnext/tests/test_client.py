# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import unittest, frappe
from frappe.utils import sel
from frappe.utils import formatdate

#selenium_tests = True

# class TestLogin(unittest.TestCase):
# 	def setUp(self):
# 		sel.login()
#
# 	def test_material_request(self):
# 		sel.new_doc("Stock", "Material Request")
# 		sel.set_field("company", "_Test Company")
# 		sel.add_child("items")
# 		sel.set_field("item_code", "_Test Item")
# 		sel.set_field("qty", "1")
# 		sel.set_field("warehouse", "_Test Warehouse - _TC")
# 		sel.set_field("schedule_date", formatdate())
# 		sel.done_add_child("items")
# 		sel.primary_action()
# 		sel.wait_for_state("clean")
