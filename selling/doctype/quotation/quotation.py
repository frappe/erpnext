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

from webnotes.utils import cstr, getdate
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql
	

from controllers.selling_controller import SellingController

class DocType(SellingController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.tname = 'Quotation Item'
		self.fname = 'quotation_details'

	def onload(self):
		self.add_communication_list()
		 
	# Pull Opportunity Details
	# --------------------
	def pull_enq_details(self):
		self.doclist = self.doc.clear_table(self.doclist, 'quotation_details')
		get_obj('DocType Mapper', 'Opportunity-Quotation').dt_map('Opportunity', 'Quotation', self.doc.enq_no, self.doc, self.doclist, "[['Opportunity', 'Quotation'],['Opportunity Item', 'Quotation Item']]")

		self.get_adj_percent()

		return self.doc.quotation_to

	# Get contact person details based on customer selected
	# ------------------------------------------------------
	def get_contact_details(self):
		return get_obj('Sales Common').get_contact_details(self,0)
	
	
		
# QUOTATION DETAILS TRIGGER FUNCTIONS
# ================================================================================		

	# Get Item Details
	# -----------------
	def get_item_details(self, args=None):
		import json
		args = args and json.loads(args) or {}
		if args.get('item_code'):
			return get_obj('Sales Common').get_item_details(args, self)
		else:
			obj = get_obj('Sales Common')
			for doc in self.doclist:
				if doc.fields.get('item_code'):
					arg = {
						'item_code': doc.fields.get('item_code'),
						'income_account': doc.fields.get('income_account'),
						'cost_center': doc.fields.get('cost_center'),
						'warehouse': doc.fields.get('warehouse')
					}
					res = obj.get_item_details(arg, self) or {}
					for r in res:
						if not doc.fields.get(r):
							doc.fields[r] = res[r]

	# Re-calculates Basic Rate & amount based on Price List Selected
	# --------------------------------------------------------------
	def get_adj_percent(self, arg=''):
		get_obj('Sales Common').get_adj_percent(self)

	
		

# OTHER CHARGES TRIGGER FUNCTIONS
# ====================================================================================
	
	# Get Tax rate if account type is TAX
	# -----------------------------------
	def get_rate(self,arg):
		return get_obj('Sales Common').get_rate(arg)

# VALIDATE
# ==============================================================================================
	
	# Fiscal Year Validation
	# ----------------------
	def validate_fiscal_year(self):
		get_obj('Sales Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.transaction_date,'Quotation Date')
	
	# Does not allow same item code to be entered twice
	# -------------------------------------------------
	def validate_for_items(self):
		chk_dupl_itm = []
		for d in getlist(self.doclist,'quotation_details'):
			if [cstr(d.item_code),cstr(d.description)] in chk_dupl_itm:
				msgprint("Item %s has been entered twice. Please change description atleast to continue" % d.item_code)
				raise Exception
			else:
				chk_dupl_itm.append([cstr(d.item_code),cstr(d.description)])


	#do not allow sales item in maintenance quotation and service item in sales quotation
	#-----------------------------------------------------------------------------------------------
	def validate_order_type(self):
		super(DocType, self).validate_order_type()
		
		if self.doc.order_type in ['Maintenance', 'Service']:
			for d in getlist(self.doclist, 'quotation_details'):
				is_service_item = sql("select is_service_item from `tabItem` where name=%s", d.item_code)
				is_service_item = is_service_item and is_service_item[0][0] or 'No'
				
				if is_service_item == 'No':
					msgprint("You can not select non service item "+d.item_code+" in Maintenance Quotation")
					raise Exception
		else:
			for d in getlist(self.doclist, 'quotation_details'):
				is_sales_item = sql("select is_sales_item from `tabItem` where name=%s", d.item_code)
				is_sales_item = is_sales_item and is_sales_item[0][0] or 'No'
				
				if is_sales_item == 'No':
					msgprint("You can not select non sales item "+d.item_code+" in Sales Quotation")
					raise Exception
	
	#--------------Validation For Last Contact Date-----------------
	# ====================================================================================================================
	def set_last_contact_date(self):
		#if not self.doc.contact_date_ref:
			#self.doc.contact_date_ref=self.doc.contact_date
			#self.doc.last_contact_date=self.doc.contact_date_ref
		if self.doc.contact_date_ref and self.doc.contact_date_ref != self.doc.contact_date:
			if getdate(self.doc.contact_date_ref) < getdate(self.doc.contact_date):
				self.doc.last_contact_date=self.doc.contact_date_ref
			else:
				msgprint("Contact Date Cannot be before Last Contact Date")
				raise Exception

	def validate(self):
		super(DocType, self).validate()
		
		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", 
			"Order Confirmed", "Order Lost", "Cancelled"])

		self.validate_fiscal_year()
		self.set_last_contact_date()
		self.validate_order_type()
		self.validate_for_items()
		sales_com_obj = get_obj('Sales Common')
		sales_com_obj.check_active_sales_items(self)
		sales_com_obj.validate_max_discount(self,'quotation_details')
		sales_com_obj.check_conversion_rate(self)
		

	def on_update(self):
		# Set Quotation Status
		webnotes.conn.set(self.doc, 'status', 'Draft')

		# subject for follow
		self.doc.subject = '[%(status)s] To %(customer)s worth %(currency)s %(grand_total)s' % self.doc.fields
	
	#update enquiry
	#------------------
	def update_enquiry(self, flag):
		prevdoc=''
		for d in getlist(self.doclist, 'quotation_details'):
			if d.prevdoc_docname:
				prevdoc = d.prevdoc_docname
		
		if prevdoc:
			if flag == 'submit': #on submit
				sql("update `tabOpportunity` set status = 'Quotation Sent' where name = %s", prevdoc)
			elif flag == 'cancel': #on cancel
				sql("update `tabOpportunity` set status = 'Open' where name = %s", prevdoc)
			elif flag == 'order lost': #order lost
				sql("update `tabOpportunity` set status = 'Opportunity Lost' where name=%s", prevdoc)
			elif flag == 'order confirm': #order confirm
				sql("update `tabOpportunity` set status='Order Confirmed' where name=%s", prevdoc)
	
	# declare as order lost
	#-------------------------
	def declare_order_lost(self,arg):
		chk = sql("select t1.name from `tabSales Order` t1, `tabSales Order Item` t2 where t2.parent = t1.name and t1.docstatus=1 and t2.prevdoc_docname = %s",self.doc.name)
		if chk:
			msgprint("Sales Order No. "+cstr(chk[0][0])+" is submitted against this Quotation. Thus 'Order Lost' can not be declared against it.")
			raise Exception
		else:
			webnotes.conn.set(self.doc, 'status', 'Order Lost')
			webnotes.conn.set(self.doc, 'order_lost_reason', arg)
			self.update_enquiry('order lost')
			return 'true'
	
	#check if value entered in item table
	#--------------------------------------
	def check_item_table(self):
		if not getlist(self.doclist, 'quotation_details'):
			msgprint("Please enter item details")
			raise Exception
		
	# ON SUBMIT
	# =========================================================================
	def on_submit(self):
		self.check_item_table()
		
		# Check for Approving Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total, self)

		# Set Quotation Status
		webnotes.conn.set(self.doc, 'status', 'Submitted')
		
		#update enquiry status
		self.update_enquiry('submit')
		
		
# ON CANCEL
# ==========================================================================
	def on_cancel(self):
		#update enquiry status
		self.update_enquiry('cancel')
		
		webnotes.conn.set(self.doc,'status','Cancelled')
			
# Print other charges
# ===========================================================================
	def print_other_charges(self,docname):
		print_lst = []
		for d in getlist(self.doclist,'other_charges'):
			lst1 = []
			lst1.append(d.description)
			lst1.append(d.total)
			print_lst.append(lst1)
		return print_lst
	
	def update_followup_details(self):
		sql("delete from `tabCommunication Log` where parent = '%s'"%self.doc.name)
		for d in getlist(self.doclist, 'follow_up'):
			d.save()
