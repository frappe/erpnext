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

import webnotes
from webnotes.utils import cstr, flt, get_defaults, nowdate
from webnotes import msgprint, errprint
from webnotes.model.code import get_obj
sql = webnotes.conn.sql
	
# -----------------------------------------------------------------------------------------

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.validated = 1
		self.data = []
		self.val_method = get_defaults()['valuation_method']

	def get_template(self):
		if self.val_method == 'Moving Average':
			return [['Item Code', 'Warehouse', 'Quantity', 'Valuation Rate']]
		else:
			return [['Item Code', 'Warehouse', 'Quantity', 'Incoming Rate']]


	def get_csv_file_data(self, submit = 1):
		"""Get csv data"""
		if submit:
			filename = self.doc.file_list.split(',')
			if not filename:
				msgprint("Please Attach File. ", raise_exception=1)
			
			from webnotes.utils import file_manager
			fn, content = file_manager.get_file(filename[1])
		
			# NOTE: Don't know why this condition exists
			if not isinstance(content, basestring) and hasattr(content, 'tostring'):
				content = content.tostring()
		else:
			content = self.doc.diff_info

		return content

	def convert_into_list(self, data, submit = 1):
		"""Convert csv data into list"""
		count = 1
		for s in data:
			count += 1
			if count == 2:
				if s[0] != 'Item Code' or s[1] != 'Warehouse':
					msgprint("First row of the attachment always should be same as template(Item Code, Warehouse, Quantity \
						and Valuation Rate/Incoming Rate)", raise_exception=1)
				else:
					continue
			# validate
			if (submit and len(s) != 4) or (not submit and len(s) != 6):
				msgprint("Data entered at Row No " + cstr(count) + " in Attachment File is not in correct format.", raise_exception=1)
				self.validated = 0
			self.validate_item(s[0], count)
			self.validate_warehouse(s[1], count)
			
			self.data.append(s)
			
		if not self.validated:
			raise Exception


	def get_reconciliation_data(self,submit = 1):
		"""Read and validate csv data"""
		import csv 
		data = csv.reader(self.get_csv_file_data(submit).splitlines())
		self.convert_into_list(data, submit)
		

	def validate_item(self, item, count):
		""" Validate item exists and non-serialized"""
		det = sql("select item_code, has_serial_no from `tabItem` where name = %s", cstr(item), as_dict = 1)
		if not det:
			msgprint("Item: " + cstr(item) + " mentioned at Row No. " + cstr(count) + "does not exist in the system")
			self.validated = 0
		elif det and det[0]['has_serial_no'] == 'Yes':
			msgprint("""You cannot make Stock Reconciliation of items having serial no. \n
			You can directly upload serial no to update their inventory. \n
			Please remove Item Code : %s at Row No. %s""" %(cstr(item), cstr(count)))
			self.validated = 0


	def validate_warehouse(self, wh, count,):
		"""Validate warehouse exists"""
		if not sql("select name from `tabWarehouse` where name = %s", cstr(wh)):
			msgprint("Warehouse: " + cstr(wh) + " mentioned at Row No. " + cstr(count) + " does not exist in the system")
			self.validated = 0



	def validate(self):
		"""Validate attachment data"""
		if self.doc.file_list:
			self.get_reconciliation_data()

			

	def get_system_stock(self, it, wh):
		"""get actual qty on reconciliation date and time as per system"""
		bin = sql("select name from tabBin where item_code=%s and warehouse=%s", (it, wh))
		prev_sle = bin and get_obj('Bin', bin[0][0]).get_prev_sle(self.doc.reconciliation_date, self.doc.reconciliation_time) or {}
		return {
			'actual_qty': prev_sle.get('bin_aqat', 0), 
			'stock_uom' : sql("select stock_uom from tabItem where name = %s", it)[0][0], 
			'val_rate'  : prev_sle.get('valuation_rate', 0)
		}

		
	def get_incoming_rate(self, row, qty_diff, sys_stock, is_submit):
		"""Calculate incoming rate to maintain valuation rate"""
		if qty_diff and is_submit:
			if self.val_method == 'Moving Average':
				in_rate = flt(row[3]) + (flt(sys_stock['actual_qty'])*(flt(row[3]) - flt(sys_stock['val_rate'])))/ flt(qty_diff)
			elif not sys_stock and not row[3]:
				msgprint("Incoming Rate is mandatory for item: %s and warehouse: %s" % (rpw[0], row[1]), raise_exception=1)
			else:
				in_rate = qty_diff > 0 and row[3] or 0
		else:
			in_rate = 0

		return in_rate


	def make_sl_entry(self, is_submit, row, qty_diff, sys_stock):
		"""Make stock ledger entry"""
		in_rate = self.get_incoming_rate(row, qty_diff, sys_stock, is_submit)
		values = [{
				'item_code'					: row[0],
				'warehouse'					: row[1],
				'transaction_date'	 		: nowdate(),
				'posting_date'				: self.doc.reconciliation_date,
				'posting_time'			 	: self.doc.reconciliation_time,
				'voucher_type'			 	: self.doc.doctype,
				'voucher_no'				: self.doc.name,
				'voucher_detail_no'			: self.doc.name,
				'actual_qty'				: flt(is_submit) * flt(qty_diff),
				'stock_uom'					: sys_stock['stock_uom'],
				'incoming_rate'				: in_rate,
				'company'					: get_defaults()['company'],
				'fiscal_year'				: get_defaults()['fiscal_year'],
				'is_cancelled'			 	: (is_submit==1) and 'No' or 'Yes',
				'batch_no'					: '',
				'serial_no'					: ''
		 }]
		get_obj('Stock Ledger', 'Stock Ledger').update_stock(values)
		

	
	def make_entry_for_valuation(self, row, sys_stock, is_submit):
		self.make_sl_entry(is_submit, row, 1, sys_stock)
		sys_stock['val_rate'] = row[3]
		sys_stock['actual_qty'] += 1
		self.make_sl_entry(is_submit, row, -1, sys_stock)


	def do_stock_reco(self, is_submit = 1):
		"""
			Make stock entry of qty diff, calculate incoming rate to maintain valuation rate.
			If no qty diff, but diff in valuation rate, make (+1,-1) entry to update valuation
		"""
		self.diff_info = ''
		for row in self.data:
			# Get qty as per system
			sys_stock = self.get_system_stock(row[0],row[1])
			
			# Diff between file and system
			qty_diff = row[2] != '~' and flt(row[2]) - flt(sys_stock['actual_qty']) or 0
			rate_diff = row[3] != '~' and flt(row[3]) - flt(sys_stock['val_rate']) or 0

			# Make sl entry
			if qty_diff:
				self.make_sl_entry(is_submit, row, qty_diff, sys_stock)
				sys_stock['actual_qty'] += qty_diff


			if (not qty_diff and rate_diff) or qty_diff < 0 and self.val_method == 'Moving Average':
				self.make_entry_for_valuation(row, sys_stock, is_submit)

			if is_submit == 1:
				r = [cstr(i) for i in row] + [cstr(qty_diff), cstr(rate_diff)]
				self.store_diff_info(r)
				
		msgprint("Stock Reconciliation Completed Successfully...")
			

	def store_diff_info(self, r):
		"""Add diffs column in attached file"""
		
		# add header
		if not self.diff_info:
			if self.val_method == 'Moving Average':
				self.diff_info += "Item Code, Warehouse, Qty, Valuation Rate, Qty Diff, Rate Diff"
			else:
				self.diff_info += "Item Code, Warehouse, Qty, Incoming Rate, Qty Diff, Rate Diff"

		
		# add data
		self.diff_info += "\n" + ','.join(r)
		
		webnotes.conn.set(self.doc, 'diff_info', self.diff_info)
		

	def on_submit(self):
		if not self.doc.file_list:
			msgprint("Please attach file before submitting.", raise_exception=1)
		else:
			self.do_stock_reco(is_submit = 1)
			

	def on_cancel(self):
		msgprint("Cancellation of stock reconciliation is temporarily suspended. The feature will come back within 2-3 days.")
		raise Exception
		self.get_reconciliation_data(submit = 0)
		self.do_stock_reco(is_submit = -1)