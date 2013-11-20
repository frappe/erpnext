# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, flt
from webnotes.model.code import get_obj
from webnotes import msgprint, _
	
class DocType:
	def __init__( self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		
	def replace_bom(self):
		self.validate_bom()
		self.update_new_bom()
		bom_list = self.get_parent_boms()
		updated_bom = []
		for bom in bom_list:
			bom_obj = get_obj("BOM", bom, with_children=1)
			updated_bom = bom_obj.update_cost_and_exploded_items(updated_bom)
			
		webnotes.msgprint(_("BOM replaced"))

	def validate_bom(self):
		if cstr(self.doc.current_bom) == cstr(self.doc.new_bom):
			msgprint("Current BOM and New BOM can not be same", raise_exception=1)
	
	def update_new_bom(self):
		current_bom_unitcost = webnotes.conn.sql("""select total_cost/quantity 
			from `tabBOM` where name = %s""", self.doc.current_bom)
		current_bom_unitcost = current_bom_unitcost and flt(current_bom_unitcost[0][0]) or 0
		webnotes.conn.sql("""update `tabBOM Item` set bom_no=%s, 
			rate=%s, amount=qty*%s where bom_no = %s and docstatus < 2""", 
			(self.doc.new_bom, current_bom_unitcost, current_bom_unitcost, self.doc.current_bom))
				
	def get_parent_boms(self):
		return [d[0] for d in webnotes.conn.sql("""select distinct parent 
			from `tabBOM Item` where ifnull(bom_no, '') = %s and docstatus < 2""",
			self.doc.new_bom)]