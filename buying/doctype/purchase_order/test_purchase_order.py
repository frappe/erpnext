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
import webnotes.defaults
from webnotes.utils import cint

class TestPurchaseOrder(unittest.TestCase):
	def test_subcontracting(self):
		po = webnotes.bean(copy=test_records[0])
		po.insert()		
		self.assertEquals(len(po.doclist.get({"parentfield": "po_raw_material_details"})), 2)

	def test_warehouse_company_validation(self):
		from controllers.buying_controller import WrongWarehouseCompany
		po = webnotes.bean(copy=test_records[0])
		po.doc.company = "_Test Company 1"
		self.assertRaises(WrongWarehouseCompany, po.insert)


test_dependencies = ["BOM"]

test_records = [
	[
		{
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"doctype": "Purchase Order", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"transaction_date": "2013-02-12", 
			"is_subcontracted": "Yes",
			"supplier": "_Test Supplier",
			"supplier_name": "_Test Supplier",
			"net_total": 5000.0, 
			"grand_total": 5000.0,
			"grand_total_import": 5000.0,
			
		}, 
		{
			"conversion_factor": 1.0, 
			"description": "_Test FG Item", 
			"doctype": "Purchase Order Item", 
			"item_code": "_Test FG Item", 
			"item_name": "_Test FG Item", 
			"parentfield": "po_details", 
			"qty": 10.0,
			"import_rate": 500.0,
			"amount": 5000.0,
			"warehouse": "_Test Warehouse", 
			"stock_uom": "Nos", 
			"uom": "_Test UOM",
		}
	],
]