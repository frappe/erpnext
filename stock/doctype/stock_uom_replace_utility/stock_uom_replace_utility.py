# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt, now, cint
from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist
from webnotes.model.code import get_obj
from webnotes import msgprint, _


class DocType:
	def __init__(self, d, dl=[]):
		self.doc, self.doclist = d,dl

	def validate_mandatory(self):
		if not cstr(self.doc.item_code):
			msgprint("Please Enter an Item.")
			raise Exception
		
		if not cstr(self.doc.new_stock_uom):
			msgprint("Please Enter New Stock UOM.")
			raise Exception

		if cstr(self.doc.current_stock_uom) == cstr(self.doc.new_stock_uom):
			msgprint("Current Stock UOM and Stock UOM are same.")
			raise Exception 
	
		# check conversion factor
		if not flt(self.doc.conversion_factor):
			msgprint("Please Enter Conversion Factor.")
			raise Exception
		
		stock_uom = webnotes.conn.sql("select stock_uom from `tabItem` where name = '%s'" % self.doc.item_code)
		stock_uom = stock_uom and stock_uom[0][0]
		if cstr(self.doc.new_stock_uom) == cstr(stock_uom):
			msgprint("Item Master is already updated with New Stock UOM " + cstr(self.doc.new_stock_uom))
			raise Exception
			
	def update_item_master(self):
		item_bean = webnotes.bean("Item", self.doc.item_code)
		item_bean.doc.stock_uom = self.doc.new_stock_uom
		item_bean.save()
		
		msgprint(_("Default UOM updated in item ") + self.doc.item_code)
		
	def update_bin(self):
		# update bin
		if flt(self.doc.conversion_factor) != flt(1):
			webnotes.conn.sql("update `tabBin` set stock_uom = '%s' , indented_qty = ifnull(indented_qty,0) * %s, ordered_qty = ifnull(ordered_qty,0) * %s, reserved_qty = ifnull(reserved_qty,0) * %s, planned_qty = ifnull(planned_qty,0) * %s, projected_qty = actual_qty + ordered_qty + indented_qty + planned_qty - reserved_qty	where item_code = '%s'" % (self.doc.new_stock_uom, self.doc.conversion_factor, self.doc.conversion_factor, self.doc.conversion_factor, self.doc.conversion_factor, self.doc.item_code) )
		else:
			webnotes.conn.sql("update `tabBin` set stock_uom = '%s' where item_code = '%s'" % (self.doc.new_stock_uom, self.doc.item_code) )

		# acknowledge user
		msgprint(" All Bins Updated Successfully.")
			
	def update_stock_ledger_entry(self):
		# update stock ledger entry
		from stock.stock_ledger import update_entries_after
		
		if flt(self.doc.conversion_factor) != flt(1):
			webnotes.conn.sql("update `tabStock Ledger Entry` set stock_uom = '%s', actual_qty = ifnull(actual_qty,0) * '%s' where item_code = '%s' " % (self.doc.new_stock_uom, self.doc.conversion_factor, self.doc.item_code))
		else:
			webnotes.conn.sql("update `tabStock Ledger Entry` set stock_uom = '%s' where item_code = '%s' " % (self.doc.new_stock_uom, self.doc.item_code))
		
		# acknowledge user
		msgprint("Stock Ledger Entries Updated Successfully.")
		
		# update item valuation
		if flt(self.doc.conversion_factor) != flt(1):
			wh = webnotes.conn.sql("select name from `tabWarehouse`")
			for w in wh:
				update_entries_after({"item_code": self.doc.item_code, "warehouse": w[0]})

		# acknowledge user
		msgprint("Item Valuation Updated Successfully.")

	# Update Stock UOM							
	def update_stock_uom(self):
		self.validate_mandatory()
		self.validate_uom_integer_type()
			
		self.update_stock_ledger_entry()
		
		self.update_bin()
		
		self.update_item_master()

		
	def validate_uom_integer_type(self):
		current_is_integer = webnotes.conn.get_value("UOM", self.doc.current_stock_uom, "must_be_whole_number")
		new_is_integer = webnotes.conn.get_value("UOM", self.doc.new_stock_uom, "must_be_whole_number")
		
		if current_is_integer and not new_is_integer:
			webnotes.msgprint("New UOM must be of type Whole Number", raise_exception=True)

		if not current_is_integer and new_is_integer:
			webnotes.msgprint("New UOM must NOT be of type Whole Number", raise_exception=True)

		if current_is_integer and new_is_integer and cint(self.doc.conversion_factor)!=self.doc.conversion_factor:
			webnotes.msgprint("Conversion Factor cannot be fraction", raise_exception=True)

@webnotes.whitelist()
def get_stock_uom(item_code):
	return { 'current_stock_uom': cstr(webnotes.conn.get_value('Item', item_code, 'stock_uom')) }
	
