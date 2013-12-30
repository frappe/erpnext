# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl

	def autoname(self):
		self.doc.name = self.doc.new_item_code
	
	def validate(self):
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

def get_new_item_code(doctype, txt, searchfield, start, page_len, filters):
	from controllers.queries import get_match_cond
	
	return webnotes.conn.sql("""select name, item_name, description from tabItem 
		where is_stock_item="No" and is_sales_item="Yes"
		and name not in (select name from `tabSales BOM`) and %s like %s
		%s limit %s, %s""" % (searchfield, "%s", 
		get_match_cond(doctype, searchfield),"%s", "%s"), 
		("%%%s%%" % txt, start, page_len))