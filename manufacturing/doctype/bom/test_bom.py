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