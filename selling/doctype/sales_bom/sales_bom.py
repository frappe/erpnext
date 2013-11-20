# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

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

		from utilities.transaction_base import validate_uom_is_integer
		validate_uom_is_integer(self.doclist, "uom", "qty")

	def validate_main_item(self):
		"""main item must have Is Stock Item as No and Is Sales Item as Yes"""
		if not webnotes.conn.sql("""select name from tabItem where name=%s and
			ifnull(is_stock_item,'')='No' and ifnull(is_sales_item,'')='Yes'""", self.doc.new_item_code):
			webnotes.msgprint("""Parent Item %s is either a Stock Item or a not a Sales Item""",
				raise_exception=1)

	def get_item_details(self, name):
		det = webnotes.conn.sql("""select description, stock_uom from `tabItem` 
			where name = %s""", name)
		return {
			'description' : det and det[0][0] or '', 
			'uom': det and det[0][1] or ''
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

def get_new_item_code(doctype, txt, searchfield, start, page_len, filters):
	from controllers.queries import get_match_cond
	
	return webnotes.conn.sql("""select name, item_name, description from tabItem 
		where is_stock_item="No" and is_sales_item="Yes"
		and name not in (select name from `tabSales BOM`) and %s like %s
		%s limit %s, %s""" % (searchfield, "%s", 
		get_match_cond(doctype, searchfield),"%s", "%s"), 
		("%%%s%%" % txt, start, page_len))