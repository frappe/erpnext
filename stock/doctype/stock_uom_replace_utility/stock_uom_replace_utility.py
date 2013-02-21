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

from webnotes.utils import cstr, flt, now
from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql
	


class DocType:
	def __init__(self, d, dl=[]):
		self.doc, self.doclist = d,dl

	def get_stock_uom(self, item_code):
		return {'current_stock_uom': cstr(webnotes.conn.get_value('Item', item_code, 'stock_uom'))}
	
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
		
		stock_uom = sql("select stock_uom from `tabItem` where name = '%s'" % self.doc.item_code)
		stock_uom = stock_uom and stock_uom[0][0]
		if cstr(self.doc.new_stock_uom) == cstr(stock_uom):
			msgprint("Item Master is already updated with New Stock UOM " + cstr(self.doc.new_stock_uom))
			raise Exception
			
	def update_item_master(self):
		# update stock uom in item master
		sql("update `tabItem` set stock_uom = '%s' where name = '%s' " % (self.doc.new_stock_uom, self.doc.item_code))
		
		# acknowledge user
		msgprint("New Stock UOM : " + cstr(self.doc.new_stock_uom) + " updated in Item : " + cstr(self.doc.item_code))
		
	def update_bin(self):
		# update bin
		if flt(self.doc.conversion_factor) != flt(1):
			sql("update `tabBin` set stock_uom = '%s' , indented_qty = ifnull(indented_qty,0) * %s, ordered_qty = ifnull(ordered_qty,0) * %s, reserved_qty = ifnull(reserved_qty,0) * %s, planned_qty = ifnull(planned_qty,0) * %s, projected_qty = actual_qty + ordered_qty + indented_qty + planned_qty - reserved_qty	where item_code = '%s'" % (self.doc.new_stock_uom, self.doc.conversion_factor, self.doc.conversion_factor, self.doc.conversion_factor, self.doc.conversion_factor, self.doc.item_code) )
		else:
			sql("update `tabBin` set stock_uom = '%s' where item_code = '%s'" % (self.doc.new_stock_uom, self.doc.item_code) )

		# acknowledge user
		msgprint(" All Bins Updated Successfully.")
			
	def update_stock_ledger_entry(self):
		# update stock ledger entry
		from stock.stock_ledger import update_entries_after
		
		if flt(self.doc.conversion_factor) != flt(1):
			sql("update `tabStock Ledger Entry` set stock_uom = '%s', actual_qty = ifnull(actual_qty,0) * '%s' where item_code = '%s' " % (self.doc.new_stock_uom, self.doc.conversion_factor, self.doc.item_code))
		else:
			sql("update `tabStock Ledger Entry` set stock_uom = '%s' where item_code = '%s' " % (self.doc.new_stock_uom, self.doc.item_code))
		
		# acknowledge user
		msgprint("Stock Ledger Entries Updated Successfully.")
		
		# update item valuation
		if flt(self.doc.conversion_factor) != flt(1):
			wh = sql("select name from `tabWarehouse`")
			for w in wh:
				update_entries_after({"item_code": self.doc.item_code, "warehouse": w[0]})

		# acknowledge user
		msgprint("Item Valuation Updated Successfully.")

	# Update Stock UOM							
	def update_stock_uom(self):
		# validate mandatory
		self.validate_mandatory()
		
		# update item master
		self.update_item_master()
		
		# update stock ledger entry
		self.update_stock_ledger_entry()
		
		# update bin
		self.update_bin()

		get_obj("Item", self.doc.item_code).on_update()
