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


	def autoname(self):
		p = self.doc.fiscal_year
		self.doc.name = make_autoname('PRO/' + self.doc.fiscal_year[2:5]+self.doc.fiscal_year[7:9] + '/.######')


	def get_item_detail(self, prod_item):
		item = sql("""select description, stock_uom, default_bom from `tabItem` 
		where (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >	now()) and name = %s""", prod_item, as_dict = 1 )
		ret = {
			'description'		: item and item[0]['description'] or '',
			'stock_uom'			: item and item[0]['stock_uom'] or '',
			'default_bom'		: item and item[0]['default_bom'] or ''
		}
		return ret


	def validate(self):
		if self.doc.production_item :
			item_detail = sql("select name from `tabItem` where name = '%s' and docstatus != 2"
			 	% self.doc.production_item, as_dict = 1)
			if not item_detail:
				msgprint("Item '%s' does not exist or cancelled in the system." 
					% cstr(self.doc.production_item), raise_exception=1)

		if self.doc.bom_no:
			bom = sql("""select name from `tabBOM`	where name = %s and docstatus = 1 
				and is_active = 'Yes' and item = %s"""
				, (self.doc.bom_no, self.doc.production_item), as_dict =1)
			if not bom:
				msgprint("""Incorrect BOM: %s entered. 
					May be BOM not exists or inactive or not submitted 
					or for some other item.""" % cstr(self.doc.bom_no), raise_exception=1)


	def stop_unstop(self, status):
		""" Called from client side on Stop/Unstop event"""
		self.update_status(status)
		qty = (flt(self.doc.qty)-flt(self.doc.produced_qty)) * ((status == 'Stopped') and -1 or 1)
		self.update_planned_qty(qty)
		msgprint("Production Order has been %s" % status)


	def update_status(self, status):
		if status == 'Stopped':
			webnotes.conn.set(self.doc, 'status', cstr(status))
		else:
			if flt(self.doc.qty) == flt(self.doc.produced_qty):
				webnotes.conn.set(self.doc, 'status', 'Completed')
			if flt(self.doc.qty) > flt(self.doc.produced_qty):
				webnotes.conn.set(self.doc, 'status', 'In Process')
			if flt(self.doc.produced_qty) == 0:
				webnotes.conn.set(self.doc, 'status', 'Submitted')


	def on_submit(self):
		webnotes.conn.set(self.doc,'status', 'Submitted')
		self.update_planned_qty(self.doc.qty)
		

	def on_cancel(self):
		# Check whether any stock entry exists against this Production Order
		stock_entry = sql("""select name from `tabStock Entry` 
			where production_order = %s and docstatus = 1""", self.doc.name)
		if stock_entry:
			msgprint("""Submitted Stock Entry %s exists against this production order. 
				Hence can not be cancelled.""" % stock_entry[0][0], raise_exception=1)

		webnotes.conn.set(self.doc,'status', 'Cancelled')
		self.update_planned_qty(-self.doc.qty)

	def update_planned_qty(self, qty):
		"""update planned qty in bin"""
		args = {
			"item_code": self.doc.production_item,
			"posting_date": nowdate(),
			"planned_qty": flt(qty)
		}
		get_obj('Warehouse', self.doc.fg_warehouse).update_bin(args)