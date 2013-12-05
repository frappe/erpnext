# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import add_days, cint,flt, nowdate, get_url_to_form, formatdate
from webnotes import msgprint, _

import webnotes.defaults


class DocType:	
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		
	def validate(self):
		if self.doc.fields.get("__islocal") or not self.doc.stock_uom:
			self.doc.stock_uom = webnotes.conn.get_value('Item', self.doc.item_code, 'stock_uom')
				
		self.validate_mandatory()
		
		self.doc.projected_qty = flt(self.doc.actual_qty) + flt(self.doc.ordered_qty) + \
		 	flt(self.doc.indented_qty) + flt(self.doc.planned_qty) - flt(self.doc.reserved_qty)
		
	def validate_mandatory(self):
		qf = ['actual_qty', 'reserved_qty', 'ordered_qty', 'indented_qty']
		for f in qf:
			if (not self.doc.fields.has_key(f)) or (not self.doc.fields[f]): 
				self.doc.fields[f] = 0.0
		
	def update_stock(self, args):
		self.update_qty(args)
		
		if args.get("actual_qty"):
			from stock.stock_ledger import update_entries_after
			
			if not args.get("posting_date"):
				args["posting_date"] = nowdate()
			
			# update valuation and qty after transaction for post dated entry
			update_entries_after({
				"item_code": self.doc.item_code,
				"warehouse": self.doc.warehouse,
				"posting_date": args.get("posting_date"),
				"posting_time": args.get("posting_time")
			})
			
	def update_qty(self, args):
		# update the stock values (for current quantities)
		self.doc.actual_qty = flt(self.doc.actual_qty) + flt(args.get("actual_qty"))
		self.doc.ordered_qty = flt(self.doc.ordered_qty) + flt(args.get("ordered_qty"))
		self.doc.reserved_qty = flt(self.doc.reserved_qty) + flt(args.get("reserved_qty"))
		self.doc.indented_qty = flt(self.doc.indented_qty) + flt(args.get("indented_qty"))
		self.doc.planned_qty = flt(self.doc.planned_qty) + flt(args.get("planned_qty"))
		
		self.doc.projected_qty = flt(self.doc.actual_qty) + flt(self.doc.ordered_qty) + \
		 	flt(self.doc.indented_qty) + flt(self.doc.planned_qty) - flt(self.doc.reserved_qty)
		
		self.doc.save()
		
	def get_first_sle(self):
		sle = webnotes.conn.sql("""
			select * from `tabStock Ledger Entry`
			where item_code = %s
			and warehouse = %s
			order by timestamp(posting_date, posting_time) asc, name asc
			limit 1
		""", (self.doc.item_code, self.doc.warehouse), as_dict=1)
		return sle and sle[0] or None