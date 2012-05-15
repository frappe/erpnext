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

# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, load_json
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.tname = 'Quotation Item'
		self.fname = 'quotation_details'
		
	# Autoname
	# ---------
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+'.#####')


# DOCTYPE TRIGGER FUNCTIONS
# ==============================================================================		
 
	# Pull Opportunity Details
	# --------------------
	def pull_enq_details(self):
		self.doc.clear_table(self.doclist, 'quotation_details')
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
					arg = {'item_code':doc.fields.get('item_code'), 'income_account':doc.fields.get('income_account'), 
						'cost_center': doc.fields.get('cost_center'), 'warehouse': doc.fields.get('warehouse')};
					ret = obj.get_item_defaults(arg)
					for r in ret:
						if not doc.fields.get(r):
							doc.fields[r] = ret[r]					


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

	# Load Default Charges
	# ----------------------------------------------------------
	def load_default_taxes(self):
		return get_obj('Sales Common').load_default_taxes(self)

	# Pull details from other charges master (Get Sales Taxes and Charges Master)
	# ----------------------------------------------------------
	def get_other_charges(self):
		return get_obj('Sales Common').get_other_charges(self)	
	
		 
# GET TERMS AND CONDITIONS
# ====================================================================================
	def get_tc_details(self):
		return get_obj('Sales Common').get_tc_details(self)

		
# VALIDATE
# ==============================================================================================
	
	# Amendment date is necessary if document is amended
	# --------------------------------------------------
	def validate_mandatory(self):
		if self.doc.amended_from and not self.doc.amendment_date:
			msgprint("Please Enter Amendment Date")
			raise Exception

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
		if self.doc.order_type == 'Maintenance':
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
			#set(self.doc, 'contact_date_ref',self.doc.contact_date)
	

	# Validate
	# --------
	def validate(self):
		self.validate_fiscal_year()
		self.validate_mandatory()
		self.set_last_contact_date()
		self.validate_order_type()
		self.validate_for_items()
		sales_com_obj = get_obj('Sales Common')
		sales_com_obj.check_active_sales_items(self)
		sales_com_obj.validate_max_discount(self,'quotation_details') #verify whether rate is not greater than max_discount
		sales_com_obj.check_conversion_rate(self)
		
		# Get total in words
		dcc = TransactionBase().get_company_currency(self.doc.company)
		self.doc.in_words = sales_com_obj.get_total_in_words(dcc, self.doc.rounded_total)
		self.doc.in_words_export = sales_com_obj.get_total_in_words(self.doc.currency, self.doc.rounded_total_export)

	def on_update(self):
		# Add to calendar
		if self.doc.contact_date and self.doc.contact_date_ref != self.doc.contact_date:
			if self.doc.contact_by:
				self.add_calendar_event()
			set(self.doc, 'contact_date_ref',self.doc.contact_date)
		
		# Set Quotation Status
		set(self.doc, 'status', 'Draft')

		# subject for follow
		self.doc.subject = '[%(status)s] To %(customer)s worth %(currency)s %(grand_total)s' % self.doc.fields

	
	# Add to Calendar
	# ====================================================================================================================
	def add_calendar_event(self):
		desc=''
		user_lst =[]
		if self.doc.customer:
			if self.doc.contact_person:
				desc = 'Contact '+cstr(self.doc.contact_person)
			else:
				desc = 'Contact customer '+cstr(self.doc.customer)
		elif self.doc.lead:
			if self.doc.lead_name:
				desc = 'Contact '+cstr(self.doc.lead_name)
			else:
				desc = 'Contact lead '+cstr(self.doc.lead)
		desc = desc+ '.By : ' + cstr(self.doc.contact_by)
		
		if self.doc.to_discuss:
			desc = desc+' To Discuss : ' + cstr(self.doc.to_discuss)
		
		ev = Document('Event')
		ev.description = desc
		ev.event_date = self.doc.contact_date
		ev.event_hour = '10:00'
		ev.event_type = 'Private'
		ev.ref_type = 'Opportunity'
		ev.ref_name = self.doc.name
		ev.save(1)
		
		user_lst.append(self.doc.owner)
		
		chk = sql("select t1.name from `tabProfile` t1, `tabSales Person` t2 where t2.email_id = t1.name and t2.name=%s",self.doc.contact_by)
		if chk:
			user_lst.append(chk[0][0])
		
		for d in user_lst:
			ch = addchild(ev, 'event_individuals', 'Event User', 0)
			ch.person = d
			ch.save(1)
	
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
			set(self.doc, 'status', 'Order Lost')
			set(self.doc, 'order_lost_reason', arg)
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
		if not self.doc.amended_from:
			set(self.doc, 'message', 'Quotation: '+self.doc.name+' has been sent')
		else:
			set(self.doc, 'message', 'Quotation has been amended. New Quotation no:'+self.doc.name)
		
		# Check for Approving Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total, self)

		# Set Quotation Status
		set(self.doc, 'status', 'Submitted')
		
		#update enquiry status
		self.update_enquiry('submit')
		
		
# ON CANCEL
# ==========================================================================
	def on_cancel(self):
		set(self.doc, 'message', 'Quotation: '+self.doc.name+' has been cancelled')
		
		#update enquiry status
		self.update_enquiry('cancel')
		
		set(self.doc,'status','Cancelled')
		
	
# SEND SMS
# =============================================================================
	def send_sms(self):
		if not self.doc.customer_mobile_no:
			msgprint("Please enter customer mobile no")
		elif not self.doc.message:
			msgprint("Please enter the message you want to send")
		else:
			msgprint(get_obj("SMS Control", "SMS Control").send_sms([self.doc.contact_mobile,], self.doc.message))
	
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
