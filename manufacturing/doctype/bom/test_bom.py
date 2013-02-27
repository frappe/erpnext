# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import unicode_literals
import unittest
import webnotes

test_records = [
	[
		{
			"doctype": "BOM", 
			"item": "_Test FG Item", 
			"quantity": 1.0,
			"is_active": 1,
			"is_default": 1,
			"docstatus": 1
		}, 
		{
			"doctype": "BOM Item", 
			"item_code": "_Test Item", 
			"parentfield": "bom_materials", 
			"qty": 1.0, 
			"rate": 5000.0, 
			"amount": 5000.0, 
			"stock_uom": "No."
		}, 
		{
			"doctype": "BOM Item", 
			"item_code": "_Test Item Home Desktop 100", 
			"parentfield": "bom_materials", 
			"qty": 2.0, 
			"rate": 1000.0,
			"amount": 2000.0,
			"stock_uom": "No."
		}
	]
]



# import webnotes.model
# from webnotes.utils import nowdate, flt
# from accounts.utils import get_fiscal_year
# from webnotes.model.doclist import DocList
# import copy
# 
# company = webnotes.conn.get_default("company")
# 
# 
# def load_data():
# 	
# 	# create default warehouse
# 	if not webnotes.conn.exists("Warehouse", "Default Warehouse"):
# 		webnotes.insert({"doctype": "Warehouse", 
# 			"warehouse_name": "Default Warehouse",
# 			"warehouse_type": "Stores"})
# 			
# 	# create UOM: Nos.
# 	if not webnotes.conn.exists("UOM", "Nos"):
# 		webnotes.insert({"doctype": "UOM", "uom_name": "Nos"})
# 	
# 	from webnotes.tests import insert_test_data
# 	# create item groups and items
# 	insert_test_data("Item Group", 
# 		sort_fn=lambda ig: (ig[0].get('parent_item_group'), ig[0].get('name')))
# 	insert_test_data("Item")
# 
# base_bom_fg = [
# 	{"doctype": "BOM", "item": "Android Jack D", "quantity": 1,
# 		"is_active": "Yes", "is_default": 1, "uom": "Nos"},
# 	{"doctype": "BOM Operation", "operation_no": 1, "parentfield": "bom_operations",
# 		"opn_description": "Development", "hour_rate": 10, "time_in_mins": 90}, 
# 	{"doctype": "BOM Item", "item_code": "Home Desktop 300", "operation_no": 1, 
# 		"qty": 2, "rate": 20, "stock_uom": "Nos", "parentfield": "bom_materials"},
# 	{"doctype": "BOM Item", "item_code": "Home Desktop 100", "operation_no": 1, 
# 		"qty": 1, "rate": 300, "stock_uom": "Nos", "parentfield": "bom_materials"},
# 	{"doctype": "BOM Item", "item_code": "Nebula 7", "operation_no": 1, 
# 			"qty": 5, "stock_uom": "Nos", "parentfield": "bom_materials"},
# ]
# 
# base_bom_child = [
# 	{"doctype": "BOM", "item": "Nebula 7", "quantity": 5,
# 		"is_active": "Yes", "is_default": 1, "uom": "Nos"},
# 	{"doctype": "BOM Operation", "operation_no": 1, "parentfield": "bom_operations",
# 		"opn_description": "Development"}, 
# 	{"doctype": "BOM Item", "item_code": "Android Jack S", "operation_no": 1, 
# 		"qty": 10, "stock_uom": "Nos", "parentfield": "bom_materials"}
# ]
# 	
# base_bom_grandchild = [
# 	{"doctype": "BOM", "item": "Android Jack S", "quantity": 1,
# 		"is_active": "Yes", "is_default": 1, "uom": "Nos"},
# 	{"doctype": "BOM Operation", "operation_no": 1, "parentfield": "bom_operations",
# 		"opn_description": "Development"}, 
# 	{"doctype": "BOM Item", "item_code": "Home Desktop 300", "operation_no": 1, 
# 		"qty": 3, "rate": 10, "stock_uom": "Nos", 	"parentfield": "bom_materials"}
# ]
# 
# 
# class TestPurchaseReceipt(unittest.TestCase):
# 	def setUp(self):
# 		webnotes.conn.begin()
# 		load_data()
# 		
# 	def test_bom_validation(self):
# 		# show throw error bacause bom no missing for sub-assembly item
# 		bom_fg = copy.deepcopy(base_bom_fg)
# 		self.assertRaises(webnotes.ValidationError, webnotes.insert, DocList(bom_fg))
# 
# 		# main item is not a manufacturing item
# 		bom_fg = copy.deepcopy(base_bom_fg)
# 		bom_fg[0]["item"] = "Home Desktop 200"
# 		bom_fg.pop(4)
# 		self.assertRaises(webnotes.ValidationError, webnotes.insert, DocList(bom_fg))
# 		
# 		# operation no mentioed in material table not matching with operation table
# 		bom_fg = copy.deepcopy(base_bom_fg)
# 		bom_fg.pop(4)
# 		bom_fg[2]["operation_no"] = 2
# 		self.assertRaises(webnotes.ValidationError, webnotes.insert, DocList(bom_fg))
# 		
# 	
# 	def test_bom(self):
# 		gc_wrapper = webnotes.insert(DocList(base_bom_grandchild))
# 		gc_wrapper.submit()
# 		
# 		bom_child = copy.deepcopy(base_bom_child)
# 		bom_child[2]["bom_no"] = gc_wrapper.doc.name
# 		child_wrapper = webnotes.insert(DocList(bom_child))
# 		child_wrapper.submit()
# 		
# 		bom_fg = copy.deepcopy(base_bom_fg)
# 		bom_fg[4]["bom_no"] = child_wrapper.doc.name
# 		fg_wrapper = webnotes.insert(DocList(bom_fg))
# 		fg_wrapper.load_from_db()
# 		
# 		self.check_bom_cost(fg_wrapper)
# 		
# 		self.check_flat_bom(fg_wrapper, child_wrapper, gc_wrapper)
# 		
# 	def check_bom_cost(self, fg_wrapper):
# 		expected_values = {
# 			"operating_cost": 15,
# 			"raw_material_cost": 640,
# 			"total_cost": 655
# 		}
# 
# 		for key in expected_values:
# 			self.assertEqual(flt(expected_values[key]), flt(fg_wrapper.doc.fields.get(key)))
# 			
# 	def check_flat_bom(self, fg_wrapper, child_wrapper, gc_wrapper):
# 		expected_flat_bom_items = {
# 			("Home Desktop 300", fg_wrapper.doc.name): (2, 20),
# 			("Home Desktop 100", fg_wrapper.doc.name): (1, 300),
# 			("Home Desktop 300", gc_wrapper.doc.name): (30, 10)
# 		}
# 		
# 		self.assertEqual(len(fg_wrapper.doclist.get({"parentfield": "flat_bom_details"})), 3)
# 		
# 		for key, val in expected_flat_bom_items.items():
# 			flat_bom = fg_wrapper.doclist.get({"parentfield": "flat_bom_details", 
# 				"item_code": key[0], "parent_bom": key[1]})[0]
# 			self.assertEqual(val, (flat_bom.qty, flat_bom.rate))
# 		
# 		
# 	def tearDown(self):
# 		webnotes.conn.rollback()