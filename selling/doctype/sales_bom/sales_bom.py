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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt
from webnotes.model.utils import getlist

class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl

	def autoname(self):
		self.doc.name = self.doc.new_item_code
	
	def validate(self):
		# check for duplicate
		self.check_duplicate()
		self.validate_main_item()

	def validate_main_item(self):
		"""main item must have Is Stock Item as No and Is Sales Item as Yes"""
		if not webnotes.conn.sql("""select name from tabItem where name=%s and
			ifnull(is_stock_item,'')='No' and ifnull(is_sales_item,'')='Yes'""", self.doc.new_item_code):
			webnotes.msgprint("""Parent Item %s is either a Stock Item or a not a Sales Item""",
				raise_exception=1)

	def get_item_details(self, name):
		det = webnotes.conn.sql("""select description, stock_uom from `tabItem` 
			where name = %s""", name)
		rate = webnotes.conn.sql("""select ref_rate from `tabItem Price` 
			where price_list_name = %s and parent = %s 
			and ref_currency = %s""", (self.doc.price_list, name, self.doc.currency))
		return {
			'description' : det and det[0][0] or '', 
			'uom': det and det[0][1] or '', 
			'rate': rate and flt(rate[0][0]) or 0.00
		}

	def check_duplicate(self, finder=0):
		il = getlist(self.doclist, "sales_bom_items")
		if not il:
			webnotes.msgprint("Add atleast one item")
			return
		
		# get all Sales BOM that have the first item	
		sbl = webnotes.conn.sql("""select distinct parent from `tabSales BOM Item` where item_code=%s 
			and parent != %s and docstatus != 2""", (il[0].item_code, self.doc.name))
		
		# check all siblings
		sub_items = [[d.item_code, flt(d.qty)] for d in il]
		
		for s in sbl:
			t = webnotes.conn.sql("""select item_code, qty from `tabSales BOM Item` where parent=%s and 
				docstatus != 2""", s[0])
			t = [[d[0], flt(d[1])] for d in t]
	
			if self.has_same_items(sub_items, t):
				webnotes.msgprint("%s has the same Sales BOM details" % s[0])
				raise Exception
		if finder:
			webnotes.msgprint("There is no Sales BOM present with the following Combination.")

	def has_same_items(self, l1, l2):
		if len(l1)!=len(l2): return 0
		for l in l2:
			if l not in l1:
				return 0
		for l in l1:
			if l not in l2:
				return 0
		return 1
