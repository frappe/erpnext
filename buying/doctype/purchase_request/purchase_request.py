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

from webnotes.utils import cstr, flt, get_defaults
from webnotes.model.wrapper import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql
	

from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.defaults = get_defaults()
		self.tname = 'Purchase Request Item'
		self.fname = 'indent_details'

	def get_default_schedule_date(self):
		get_obj(dt = 'Purchase Common').get_default_schedule_date(self)
	
	# get available qty at warehouse
	def get_bin_details(self, arg = ''):
		return get_obj(dt='Purchase Common').get_bin_details(arg)

	# Pull Sales Order Items
	# -------------------------
	def pull_so_details(self):
		self.check_if_already_pulled()
		if self.doc.sales_order_no:
			get_obj('DocType Mapper', 'Sales Order-Purchase Request', with_children=1).dt_map('Sales Order', 'Purchase Request', self.doc.sales_order_no, self.doc, self.doclist, "[['Sales Order', 'Purchase Request'],['Sales Order Item', 'Purchase Request Item']]")
			self.get_item_defaults()
		else:
			msgprint("Please select Sales Order whose details need to pull")

	def check_if_already_pulled(self):
		pass#if self.[d.sales_order_no for d in getlist(self.doclist, 'indent_details')]


	# Get item's other details
	#- ------------------------
	def get_item_defaults(self):
		self.get_default_schedule_date()
		for d in getlist(self.doclist, 'indent_details'):
			det = sql("select min_order_qty from tabItem where name = '%s'" % d.item_code)
			d.min_order_qty = det and flt(det[0][0]) or 0

	# Validate so items
	# ----------------------------
	def validate_qty_against_so(self):
		so_items = {} # Format --> {'SO/00001': {'Item/001': 120, 'Item/002': 24}}
		for d in getlist(self.doclist, 'indent_details'):
			if d.sales_order_no:
				if not so_items.has_key(d.sales_order_no):
					so_items[d.sales_order_no] = {d.item_code: flt(d.qty)}
				else:
					if not so_items[d.sales_order_no].has_key(d.item_code):
						so_items[d.sales_order_no][d.item_code] = flt(d.qty)
					else:
						so_items[d.sales_order_no][d.item_code] += flt(d.qty)
		
		for so_no in so_items.keys():
			for item in so_items[so_no].keys():
				already_indented = sql("select sum(qty) from `tabPurchase Request Item` where item_code = '%s' and sales_order_no = '%s' and docstatus = 1 and parent != '%s'" % (item, so_no, self.doc.name))
				already_indented = already_indented and flt(already_indented[0][0]) or 0
				
				actual_so_qty = sql("select sum(qty) from `tabSales Order Item` where parent = '%s' and item_code = '%s' and docstatus = 1 group by parent" % (so_no, item))
				actual_so_qty = actual_so_qty and flt(actual_so_qty[0][0]) or 0

				if flt(so_items[so_no][item]) + already_indented > actual_so_qty:
					msgprint("You can raise indent of maximum qty: %s for item: %s against sales order: %s\n Anyway, you can add more qty in new row for the same item." % (actual_so_qty - already_indented, item, so_no), raise_exception=1)
				
		
	# Validate fiscal year
	# ----------------------------
	def validate_fiscal_year(self):
		get_obj(dt = 'Purchase Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.transaction_date,'Purchase Request Date')

	# GET TERMS & CONDITIONS
	#-----------------------------
	def get_tc_details(self):
		return get_obj('Purchase Common').get_tc_details(self)
		
	# Validate Schedule Date
	#--------------------------------
	def validate_schedule_date(self):
		 #:::::::: validate schedule date v/s indent date ::::::::::::
		for d in getlist(self.doclist, 'indent_details'):
			if d.schedule_date < self.doc.transaction_date:
				msgprint("Expected Schedule Date cannot be before Purchase Request Date")
				raise Exception
				
	# Validate
	# ---------------------
	def validate(self):
		super(DocType, self).validate()
		
		self.validate_schedule_date()
		self.validate_fiscal_year()
		
		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Stopped", 
			"Cancelled"])

		# Get Purchase Common Obj
		pc_obj = get_obj(dt='Purchase Common')


		# Validate for items
		pc_obj.validate_for_items(self)
		
		# Validate qty against SO
		self.validate_qty_against_so()

	
	def update_bin(self, is_submit, is_stopped):
		""" Update Quantity Requested for Purchase in Bin"""
		
		for d in getlist(self.doclist, 'indent_details'):
			if webnotes.conn.get_value("Item", d.item_code, "is_stock_item") == "Yes":
				if not d.warehouse:
					msgprint("Please Enter Warehouse for Item %s as it is stock item" 
						% cstr(d.item_code), raise_exception=1)
						
				qty =flt(d.qty)
				if is_stopped:
					qty = (d.qty > d.ordered_qty) and flt(flt(d.qty) - flt(d.ordered_qty)) or 0
				
				args = {
					"item_code": d.item_code,
					"indented_qty": (is_submit and 1 or -1) * flt(qty),
					"posting_date": self.doc.transaction_date
				}
				get_obj('Warehouse', d.warehouse).update_bin(args)		
		
	def on_submit(self):
		purchase_controller = webnotes.get_obj("Purchase Common")
		purchase_controller.is_item_table_empty(self)
		
		webnotes.conn.set(self.doc,'status','Submitted')
		self.update_bin(is_submit = 1, is_stopped = 0)
	
	def check_modified_date(self):
		mod_db = sql("select modified from `tabPurchase Request` where name = '%s'" % self.doc.name)
		date_diff = sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.doc.modified)))
		
		if date_diff and date_diff[0][0]:
			msgprint(cstr(self.doc.doctype) +" => "+ cstr(self.doc.name) +" has been modified. Please Refresh. ")
			raise Exception

	def update_status(self, status):
		self.check_modified_date()
		# Step 1:=> Update Bin
		self.update_bin(is_submit = (status == 'Submitted') and 1 or 0, is_stopped = 1)

		# Step 2:=> Set status 
		webnotes.conn.set(self.doc,'status',cstr(status))
		
		# Step 3:=> Acknowledge User
		msgprint(self.doc.doctype + ": " + self.doc.name + " has been %s." % ((status == 'Submitted') and 'Unstopped' or cstr(status)) )
 

	def on_cancel(self):
		# Step 1:=> Get Purchase Common Obj
		pc_obj = get_obj(dt='Purchase Common')
		
		# Step 2:=> Check for stopped status
		pc_obj.check_for_stopped_status( self.doc.doctype, self.doc.name)
		
		# Step 3:=> Check if Purchase Order has been submitted against current Purchase Request
		pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Order', docname = self.doc.name, detail_doctype = 'Purchase Order Item')
		# Step 4:=> Update Bin
		self.update_bin(is_submit = 0, is_stopped = (cstr(self.doc.status) == 'Stopped') and 1 or 0)
		
		# Step 5:=> Set Status
		webnotes.conn.set(self.doc,'status','Cancelled')
