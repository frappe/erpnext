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
import webnotes, unittest

from webnotes.utils import flt
from webnotes.model.code import get_obj

class TestValuationControl(unittest.TestCase):
	def setUp(self):
		webnotes.conn.begin()

	def tearDown(self):
		webnotes.conn.rollback()
		
	def test_fifo_rate(self):
		"""test fifo rate"""
		fcfs_stack = [[40,500.0], [12,400.0]]
		self.assertTrue(DocType(None, None).get_fifo_rate(fcfs_stack)==((40*500.0 + 12*400.0)/52.0))
	
	def test_serial_no_value(self):
		"""test serial no value"""
		from webnotes.model.doc import Document

		Document(fielddata = {
			'doctype': 'Item',
			'docstatus': 0,
			'name': 'it',
			'item_name': 'it',
			'item_code': 'it',
			'item_group': 'Default',
			'is_stock_item': 'Yes',
			'has_serial_no': 'Yes',
			'stock_uom': 'Nos',
			'is_sales_item': 'Yes',
			'is_purchase_item': 'Yes',
			'is_service_item': 'No',
			'is_sub_contracted_item': 'No',
			'is_pro_applicable': 'Yes',
			'is_manufactured_item': 'Yes'		
		}).save(1)
		
		s1 = Document(fielddata= {
			'doctype':'Serial No',
			'serial_no':'s1',
			'item_code':'it',
			'purchase_rate': 100.0
		})
		s2 = Document(fielddata = s1.fields.copy())
		s3 = Document(fielddata = s1.fields.copy())
		s4 = Document(fielddata = s1.fields.copy())
		s1.save(1)
		s2.purchase_rate = 120.0
		s2.serial_no = 's2'
		s2.save(1)
		s3.purchase_rate = 130.0
		s3.serial_no = 's3'
		s3.save(1)
		s4.purchase_rate = 150.0
		s4.serial_no = 's4'
		s4.save(1)
		
		r = DocType(None, None).get_serializable_inventory_rate('s1,s2,s3')
		self.assertTrue(flt(r) - (100.0+120.0+130.0)/3 < 0.0001)


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def get_fifo_rate(self, fcfs_stack):
		"""get FIFO (average) Rate from Stack"""
		if not fcfs_stack:
			return 0.0
			
		total = sum(f[0] for f in fcfs_stack)
		if not total:
			return 0.0
		
		return sum(f[0] * f[1] for f in fcfs_stack) / total
			
	def get_serializable_inventory_rate(self, serial_no):
		"""get average value of serial numbers"""
		
		sr_nos = get_obj("Stock Ledger").get_sr_no_list(serial_no)
		return webnotes.conn.sql("""select avg(ifnull(purchase_rate, 0)) 
			from `tabSerial No` where name in ("%s")""" % '", "'.join(sr_nos))[0][0] or 0.0


	def get_valuation_method(self, item_code):
		"""get valuation method from item or default"""
		val_method = webnotes.conn.get_value('Item', item_code, 'valuation_method')
		if not val_method:
			from webnotes.utils import get_defaults
			val_method = get_defaults().get('valuation_method', 'FIFO')
		return val_method
		

	def get_incoming_rate(self, posting_date, posting_time, item, warehouse, qty = 0, serial_no = ''):
		"""Get Incoming Rate based on valuation method"""
		in_rate = 0
		val_method = self.get_valuation_method(item)
		bin_obj = get_obj('Warehouse',warehouse).get_bin(item)
		if serial_no:
			in_rate = self.get_serializable_inventory_rate(serial_no)
		elif val_method == 'FIFO':
			# get rate based on the last item value?
			if qty:
				prev_sle = bin_obj.get_prev_sle(posting_date, posting_time)
				if not prev_sle:
					return 0.0
				fcfs_stack = eval(str(prev_sle.get('fcfs_stack', '[]')))
				in_rate = fcfs_stack and self.get_fifo_rate(fcfs_stack) or 0
		elif val_method == 'Moving Average':
			prev_sle = bin_obj.get_prev_sle(posting_date, posting_time)
			in_rate = prev_sle and prev_sle.get('valuation_rate', 0) or 0
		return in_rate
