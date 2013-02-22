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
import copy

from webnotes.model.bean import Bean
from webnotes.model.doc import Document
from webnotes.utils import flt

sql = webnotes.conn.sql


class TestItem(unittest.TestCase):
	def setUp(self):
		webnotes.conn.begin()

	def tearDown(self):
		webnotes.conn.rollback()
		
	def testInsert(self):
		d = Bean()

		count_before =  flt(sql("select count(*) from tab"+_doctype)[0][0])
		if docok:
			for i in docok:
				d.doc = i
				d.children = None
				d.doc.fields['__islocal']=1
				d.save(1)
		count_after = flt(sql("select count(*) from tab"+_doctype)[0][0])
		self.assertTrue(count_before+len(docok)==count_after)
	
	def testFailAssert(self):
		if docnotok:
			with self.assertRaises(Exception) as context:
				d = Bean()
				d.doc = docnotok[0]
				d.children = None
				d.doc.fields['__islocal']=1
				d.save(1)

# Test Data

tabOK = [
		{'is_purchase_item': None, 'is_pro_applicable': 'No', 'is_manufactured_item': None, 'description': 'Gel Ink', 'default_warehouse': None, 'item_name': 'Gel Ink', 'item_group': 'Ink', 'item_code': 'GELINK', 'is_sub_contracted_item': None, 'is_stock_item': 'Yes', 'stock_uom': 'Nos', 'docstatus': '0'}, 
		{'is_purchase_item': None, 'is_pro_applicable': 'No', 'is_manufactured_item': None, 'description': 'Gel Refill', 'default_warehouse': None, 'item_name': 'Gel Refill', 'item_group': 'Refill', 'item_code': 'GELREF', 'is_sub_contracted_item': None, 'is_stock_item': 'Yes', 'stock_uom': 'Nos', 'docstatus': '0'}, 
		{'is_purchase_item': None, 'is_pro_applicable': 'No', 'is_manufactured_item': None, 'description': 'Gel Pen', 'default_warehouse': None, 'item_name': 'Gel Pen', 'item_group': 'Pen', 'item_code': 'GELPEN', 'is_sub_contracted_item': None, 'is_stock_item': 'Yes', 'stock_uom': 'Nos', 'docstatus': '0'}
	]

tabNotOK =	[
			{'is_purchase_item': None, 'is_pro_applicable': None, 'is_manufactured_item': None, 'description': 'F Ink', 'default_warehouse': None, 'item_name': 'F Ink', 'item_group': 'F Ink', 'item_code': None, 'is_sub_contracted_item': None, 'is_stock_item': 'No', 'stock_uom': 'Nos', 'docstatus': '0'}
		]
	      
_doctype = 'Item'

for i in tabOK: i['doctype']=_doctype
for i in tabNotOK: i['doctype']=_doctype

docok = [Document(fielddata=r) for r in tabOK]
docnotok = [Document(fielddata=r) for r in tabNotOK]


test_records = [
	[{
		"doctype": "Item",
		"item_code": "_Test Item",
		"item_name": "_Test Item",
		"description": "_Test Item",
		"item_group": "_Test Item Group",
		"is_stock_item": "Yes",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"is_sample_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	}, {
		"doctype": "Item Reorder",
		"parentfield": "item_reorder",
		"warehouse": "_Test Warehouse",
		"warehouse_reorder_level": 20,
		"warehouse_reorder_qty": 20
	}],
	[{
		"doctype": "Item",
		"item_code": "_Test Item Home Desktop 100",
		"item_name": "_Test Item Home Desktop 100",
		"description": "_Test Item Home Desktop 100",
		"item_group": "_Test Item Group Desktops",
		"is_stock_item": "Yes",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"is_sample_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	},
	{
		"doctype": "Item Tax",
		"tax_type": "_Test Account Excise Duty - _TC",
		"tax_rate": 10
	}],
	[{
		"doctype": "Item",
		"item_code": "_Test Item Home Desktop 200",
		"item_name": "_Test Item Home Desktop 200",
		"description": "_Test Item Home Desktop 200",
		"item_group": "_Test Item Group Desktops",
		"is_stock_item": "Yes",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"is_sample_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	}],
	[{
		"doctype": "Item",
		"item_code": "_Test Sales BOM Item",
		"item_name": "_Test Sales BOM Item",
		"description": "_Test Sales BOM Item",
		"item_group": "_Test Item Group Desktops",
		"is_stock_item": "No",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"is_sample_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	}],
]