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
import webnotes

from webnotes.utils import cint, getdate, nowdate
import datetime
from webnotes import msgprint
	
from controllers.stock_controller import StockController

class DocType(StockController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate_amc_status(self):
		"""
			validate amc status
		"""
		if (self.doc.maintenance_status == 'Out of AMC' and self.doc.amc_expiry_date and getdate(self.doc.amc_expiry_date) >= datetime.date.today()) or (self.doc.maintenance_status == 'Under AMC' and (not self.doc.amc_expiry_date or getdate(self.doc.amc_expiry_date) < datetime.date.today())):
			msgprint("AMC expiry date and maintenance status mismatch. Please verify", raise_exception=1)

	def validate_warranty_status(self):
		"""
			validate warranty status	
		"""
		if (self.doc.maintenance_status == 'Out of Warranty' and self.doc.warranty_expiry_date and getdate(self.doc.warranty_expiry_date) >= datetime.date.today()) or (self.doc.maintenance_status == 'Under Warranty' and (not self.doc.warranty_expiry_date or getdate(self.doc.warranty_expiry_date) < datetime.date.today())):
			msgprint("Warranty expiry date and maintenance status mismatch. Please verify", raise_exception=1)


	def validate_warehouse(self):
		if self.doc.status=='In Store' and not self.doc.warehouse:
			msgprint("Warehouse is mandatory if this Serial No is <b>In Store</b>", raise_exception=1)

	def validate_item(self):
		"""
			Validate whether serial no is required for this item
		"""
		item = webnotes.conn.sql("select name, has_serial_no from tabItem where name = '%s'" % self.doc.item_code)
		if not item:
			msgprint("Item is not exists in the system", raise_exception=1)
		elif item[0][1] == 'No':
			msgprint("To proceed please select 'Yes' in 'Has Serial No' in Item master: '%s'" % self.doc.item_code, raise_exception=1)
			

	def validate(self):
		self.validate_warranty_status()
		self.validate_amc_status()
		self.validate_warehouse()
		self.validate_item()

	def on_update(self):
		if self.doc.warehouse and self.doc.status == 'In Store' \
				and cint(self.doc.sle_exists) == 0 and \
				not webnotes.conn.sql("""select name from `tabStock Ledger Entry` 
				where serial_no = %s and ifnull(is_cancelled, 'No') = 'No'""", self.doc.name):
			self.make_stock_ledger_entry(1)
			webnotes.conn.set(self.doc, 'sle_exists', 1)
			
			self.make_gl_entries()

	def make_stock_ledger_entry(self, qty):
		from webnotes.model.code import get_obj
		values = [{
			'item_code'				: self.doc.item_code,
			'warehouse'				: self.doc.warehouse,
			'transaction_date'		: nowdate(),
			'posting_date'			: self.doc.purchase_date or (self.doc.creation and self.doc.creation.split(' ')[0]) or nowdate(),
			'posting_time'			: self.doc.purchase_time or '00:00',
			'voucher_type'			: 'Serial No',
			'voucher_no'			: self.doc.name,
			'voucher_detail_no'	 	: '', 
			'actual_qty'			: qty, 
			'stock_uom'				: webnotes.conn.get_value('Item', self.doc.item_code, 'stock_uom'),
			'incoming_rate'			: self.doc.purchase_rate,
			'company'				: self.doc.company,
			'fiscal_year'			: self.doc.fiscal_year,
			'is_cancelled'			: 'No', # is_cancelled is always 'No' because while deleted it can not find creation entry if it not created directly, voucher no != serial no
			'batch_no'				: '',
			'serial_no'				: self.doc.name
		}]
		get_obj('Stock Ledger').update_stock(values)


	def on_trash(self):
		if self.doc.status == 'Delivered':
			msgprint("Cannot trash Serial No : %s as it is already Delivered" % (self.doc.name), raise_exception = 1)
		elif self.doc.status == 'In Store': 
			webnotes.conn.set(self.doc, 'status', 'Not in Use')
			self.make_stock_ledger_entry(-1)
			
			if cint(webnotes.defaults.get_global_default("auto_inventory_accounting")) \
				and webnotes.conn.sql("""select name from `tabGL Entry`
				where voucher_type=%s and voucher_no=%s and ifnull(is_cancelled, 'No')='No'""",
				(self.doc.doctype, self.doc.name)):
					self.make_gl_entries(cancel=True)


	def on_cancel(self):
		self.on_trash()

	def on_restore(self):
		self.make_stock_ledger_entry(1)
		self.make_gl_entries()
	
	def on_rename(self, new, old):
		"""rename serial_no text fields"""
		for dt in webnotes.conn.sql("""select parent from tabDocField 
			where fieldname='serial_no' and fieldtype='Text'"""):
			
			for item in webnotes.conn.sql("""select name, serial_no from `tab%s` 
				where serial_no like '%%%s%%'""" % (dt[0], old)):
				
				serial_nos = map(lambda i: i==old and new or i, item[1].split('\n'))
				webnotes.conn.sql("""update `tab%s` set serial_no = %s 
					where name=%s""" % (dt[0], '%s', '%s'),
					('\n'.join(serial_nos), item[0]))

	def make_gl_entries(self, cancel=False):
		if not cint(webnotes.defaults.get_global_default("auto_inventory_accounting")):
			return
				
		from accounts.general_ledger import make_gl_entries
		against_stock_account = self.get_company_default("stock_adjustment_account")
		gl_entries = self.get_gl_entries_for_stock(against_stock_account, self.doc.purchase_rate)
		
		for entry in gl_entries:
			entry["posting_date"] = self.doc.purchase_date
			
		if gl_entries:
			make_gl_entries(gl_entries, cancel)