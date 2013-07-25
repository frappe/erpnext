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

from webnotes.utils import cstr, flt, nowdate
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate(self):
		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Stopped", 
			"In Process", "Completed", "Cancelled"])

		if self.doc.production_item :
			item_detail = sql("select name from `tabItem` where name = '%s' and docstatus != 2"
			 	% self.doc.production_item, as_dict = 1)
			if not item_detail:
				msgprint("Item '%s' does not exist or cancelled in the system." 
					% cstr(self.doc.production_item), raise_exception=1)

		if self.doc.bom_no:
			bom = sql("""select name from `tabBOM` where name=%s and docstatus=1 
				and is_active=1 and item=%s"""
				, (self.doc.bom_no, self.doc.production_item), as_dict =1)
			if not bom:
				msgprint("""Incorrect BOM: %s entered. 
					May be BOM not exists or inactive or not submitted 
					or for some other item.""" % cstr(self.doc.bom_no), raise_exception=1)
					
		if self.doc.sales_order:
			if not webnotes.conn.sql("""select name from `tabSales Order` 
					where name=%s and docstatus = 1""", self.doc.sales_order):
				msgprint("Sales Order: %s is not valid" % self.doc.sales_order, raise_exception=1)
				
			self.validate_production_order_against_so()

		from utilities.transaction_base import validate_uom_is_integer
		validate_uom_is_integer(self.doclist, "stock_uom", ["qty", "produced_qty"])

	
	def validate_production_order_against_so(self):
		# already ordered qty
		ordered_qty_against_so = webnotes.conn.sql("""select sum(qty) from `tabProduction Order`
			where production_item = %s and sales_order = %s and docstatus < 2""", 
			(self.doc.production_item, self.doc.sales_order))[0][0]

		total_qty = flt(ordered_qty_against_so) + flt(self.doc.qty)
		
		# get qty from Sales Order Item table
		so_item_qty = webnotes.conn.sql("""select sum(qty) from `tabSales Order Item` 
			where parent = %s and item_code = %s""", 
			(self.doc.sales_order, self.doc.production_item))[0][0]
		# get qty from Packing Item table
		dnpi_qty = webnotes.conn.sql("""select sum(qty) from `tabDelivery Note Packing Item` 
			where parent = %s and parenttype = 'Sales Order' and item_code = %s""", 
			(self.doc.sales_order, self.doc.production_item))[0][0]
		# total qty in SO
		so_qty = flt(so_item_qty) + flt(dnpi_qty)
				
		if total_qty > so_qty:
			webnotes.msgprint("""Total production order qty for item: %s against sales order: %s \
			 	will be %s, which is greater than sales order qty (%s). 
				Please reduce qty or remove the item.""" %
				(self.doc.production_item, self.doc.sales_order, 
					total_qty, so_qty), raise_exception=1)


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

@webnotes.whitelist()	
def get_item_details(item):
	res = webnotes.conn.sql("""select stock_uom
		from `tabItem` where (ifnull(end_of_life, "")="" or end_of_life > now())
		and name=%s""", (item,), as_dict=1)
	
	if not res:
		return {}
		
	res = res[0]
	bom = webnotes.conn.sql("""select name from `tabBOM` where item=%s 
		and ifnull(is_default, 0)=1""", (item,))
	if bom:
		res.bom_no = bom[0][0]
		
	return res