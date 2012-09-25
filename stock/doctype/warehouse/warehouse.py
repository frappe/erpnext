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

# Please edit this list and import only required elements
from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		
	def get_bin(self, item_code):
		bin = sql("select name from tabBin where item_code = %s and \
				warehouse = %s", (item_code, self.doc.name))
		bin = bin and bin[0][0] or ''
		if not bin:
			if not self.doc.warehouse_type :
				msgprint("[Warehouse Type is Mandatory] Please Enter warehouse type in Warehouse " + self.doc.name)
				raise Exception
			bin = Document('Bin')
			bin.item_code = item_code
			bin.stock_uom = get_value('Item', item_code, 'stock_uom')
			bin.warehouse = self.doc.name
			bin.warehouse_type = self.doc.warehouse_type
			bin_obj = get_obj(doc=bin)
			bin_obj.validate()
			bin.save(1)
			bin = bin.name
		else:
			bin_obj = get_obj('Bin',bin)

		return bin_obj
	

	def validate_asset(self, item_code):
		if sql("select is_asset_item from tabItem where name=%s", item_code)[0][0] == 'Yes' and self.doc.warehouse_type != 'Fixed Asset':
			msgprint("Fixed Asset Item %s can only be transacted in a Fixed Asset type Warehouse" % item_code)
			raise Exception


	# update bin
	# ----------
	def update_bin(self, actual_qty, reserved_qty, ordered_qty, indented_qty, planned_qty, item_code, dt, sle_id = '',posting_time = '', serial_no = '', is_cancelled = 'No',doc_type='',doc_name='',is_amended='No'):
		self.validate_asset(item_code)
		it_det = get_value('Item', item_code, 'is_stock_item')
		if it_det and it_det == 'Yes':
			bin = self.get_bin(item_code)
			bin.update_stock(actual_qty, reserved_qty, ordered_qty, indented_qty, planned_qty, dt, sle_id, posting_time, serial_no, is_cancelled,doc_type,doc_name,is_amended)
			return bin
		else:
			msgprint("[Stock Update] Ignored %s since it is not a stock item" % item_code)

	# repost stock
	# ------------
	def repost_stock(self):
		bl = sql("select name from tabBin where warehouse=%s", self.doc.name)
		for b in bl:
			bobj = get_obj('Bin',b[0])
			bobj.update_entries_after(posting_date = '0000-00-00', posting_time = '00:00')

			sql("COMMIT")
			sql("START TRANSACTION")

	def check_state(self):
		return "\n" + "\n".join([i[0] for i in sql("select state_name from `tabState` where `tabState`.country='%s' " % self.doc.country)])

	def validate(self):
		if self.doc.email_id:
			if not validate_email_add(self.doc.email_id):
				msgprint("Please enter valid Email Id.")
				raise Exception
		if not self.doc.warehouse_type:
			msgprint("[Warehouse Type is Mandatory] Please Enter	Please Entry warehouse type in Warehouse " + self.doc.name)
			raise Exception
		wt = sql("select warehouse_type from `tabWarehouse` where name ='%s'" % self.doc.name)
		if cstr(self.doc.warehouse_type) != cstr(wt and wt[0][0] or ''):
			sql("update `tabStock Ledger Entry` set warehouse_type = '%s' where warehouse = '%s'" % (self.doc.warehouse_type, self.doc.name))
			msgprint("All Stock Ledger Entries Updated.")
			
	def on_trash(self):
		# delete bin
		bins = sql("select * from `tabBin` where warehouse = %s", self.doc.name, as_dict=1)
		for d in bins:
			if d['actual_qty'] or d['reserved_qty'] or d['ordered_qty'] or d['indented_qty'] or d['projected_qty'] or d['planned_qty']:
				msgprint("Warehouse: %s can not be deleted as qty exists for item: %s" % (self.doc.name, d['item_code']), raise_exception=1)
			else:
				sql("delete from `tabBin` where name = %s", d['name'])
				
		# delete cancelled sle
		if sql("select name from `tabStock Ledger Entry` where warehouse = %s and ifnull('is_cancelled', '') = 'No'", self.doc.name):
			mdgprint("Warehosue can not be deleted as stock ledger entry exists for this warehosue.", raise_exception=1)
		else:
			sql("delete from `tabStock Ledger Entry` where warehouse = %s", self.doc.name)
