# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe
import unittest
test_records = frappe.get_test_records('Warehouse')

class TestWarehouse(unittest.TestCase):
	def test_parent_warehouse(self):
		parent_warehouse = frappe.get_doc("Warehouse", "_Test Warehouse Group - _TC")
		self.assertEquals(parent_warehouse.is_group, 1)
		
	def test_warehouse_hierarchy(self):
		p_warehouse = frappe.get_doc("Warehouse", "_Test Warehouse Group - _TC")
		
		child_warehouses =  frappe.db.sql("""select name, is_group, parent_warehouse from `tabWarehouse` wh
			where wh.lft > %s and wh.rgt < %s""", (p_warehouse.lft, p_warehouse.rgt), as_dict=1)
		
		for child_warehouse in child_warehouses:
			self.assertEquals(p_warehouse.name, child_warehouse.parent_warehouse)
			self.assertEquals(child_warehouse.is_group, 0)
		
		
