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
from webnotes.model.doc import Document

# Material  Receipt
#-----------------------

mr = [
	Document(
		fielddata = {
			'doctype': 'Stock Entry',
			'posting_date': '2011-09-01',
			'transfer_date': '2011-09-01',
			'posting_time': '12:00',
			'company': 'comp',
			'fiscal_year' : '2011-2012',
			'purpose': 'Material Receipt',
			'name': 'mr'
		}
	),
	Document(
		fielddata  ={
			'doctype': 'Stock Entry Detail',
			'parenttype': 'Stock Entry',
			'parentfield' : 'mtn_details',
			'parent' : 'mr',
			'item_code' : 'it',
			't_warehouse' : 'wh1',
			'qty' : 10,
			'transfer_qty' : 10,
			'incoming_rate': 100,
			'stock_uom': 'Nos',
			'conversion_factor': 1,
			'serial_no': 'srno1, srno2, srno3, srno4, srno5, srno6, srno7, srno8, srno9, srno10'	
		}
	)
]

mr1 = [
	Document(
		fielddata = {
			'doctype': 'Stock Entry',
			'posting_date': '2011-09-01',
			'transfer_date': '2011-09-01',
			'posting_time': '12:00',
			'company': 'comp',
			'fiscal_year' : '2011-2012',
			'purpose': 'Material Receipt',
			'name': 'mr1'
		}
	),
	Document(
		fielddata  ={
			'doctype': 'Stock Entry Detail',
			'parenttype': 'Stock Entry',
			'parentfield' : 'mtn_details',
			'parent' : 'mr1',
			'item_code' : 'it',
			't_warehouse' : 'wh1',
			'qty' : 5,
			'transfer_qty' : 5,
			'incoming_rate': 400,
			'stock_uom': 'Nos',
			'conversion_factor': 1,
			'serial_no': 'srno11, srno12, srno13, srno14, srno15'	
		}
	)
]


# Material Transfer
#--------------------

mtn = [
	Document(
		fielddata = {
			'doctype': 'Stock Entry',
			'posting_date': '2011-09-01',
			'transfer_date': '2011-09-01',
			'posting_time': '12:00',
			'company': 'comp',
			'fiscal_year' : '2011-2012',
			'purpose': 'Material Transfer',
			'name': 'mtn'
		}
	),
	Document(
		fielddata  ={
			'doctype': 'Stock Entry Detail',
			'parenttype': 'Stock Entry',
			'parentfield' : 'mtn_details',
			'parent' : 'mtn',
			'item_code' : 'it',
			's_warehouse' : 'wh1',
			't_warehouse' : 'wh2',
			'qty' : 5,
			'transfer_qty' : 5,
			'incoming_rate': 100,
			'stock_uom': 'Nos',
			'conversion_factor': 1,
			'serial_no': 'srno1, srno2, srno3, srno4, srno5'	
		}
	)
]

# Material Issue
#--------------------

mi = [
	Document(
		fielddata = {
			'doctype': 'Stock Entry',
			'posting_date': '2011-09-01',
			'transfer_date': '2011-09-01',
			'posting_time': '14:00',
			'company': 'comp',
			'fiscal_year' : '2011-2012',
			'purpose': 'Material Issue',
			'name': 'mi'
		}
	),
	Document(
		fielddata  ={
			'doctype': 'Stock Entry Detail',
			'parenttype': 'Stock Entry',
			'parentfield' : 'mtn_details',
			'parent' : 'mi',
			'item_code' : 'it',
			's_warehouse' : 'wh1',
			'qty' : 4,
			'transfer_qty' : 4,
			'incoming_rate': 100,
			'stock_uom': 'Nos',
			'conversion_factor': 1,
			'serial_no': 'srno1, srno2, srno3, srno4'
		}
	)
]
