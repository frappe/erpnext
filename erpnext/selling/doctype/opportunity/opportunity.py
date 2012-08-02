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

# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
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
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.fname = 'enq_details'
		self.tname = 'Opportunity Item'

	# Autoname
	# ====================================================================================================================
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+'.####')

	#--------Get customer address-------
	# ====================================================================================================================
	def get_cust_address(self,name):
		details = sql("select customer_name, address, territory, customer_group from `tabCustomer` where name = '%s' and docstatus != 2" %(name), as_dict = 1)
		if details:
			ret = {
				'customer_name':	details and details[0]['customer_name'] or '',
				'address'	:	details and details[0]['address'] or '',
				'territory'			 :	details and details[0]['territory'] or '',
				'customer_group'		:	details and details[0]['customer_group'] or ''
			}
			# ********** get primary contact details (this is done separately coz. , in case there is no primary contact thn it would not be able to fetch customer details in case of join query)

			contact_det = sql("select contact_name, contact_no, email_id from `tabContact` where customer = '%s' and is_customer = 1 and is_primary_contact = 'Yes' and docstatus != 2" %(name), as_dict = 1)

			
			ret['contact_person'] = contact_det and contact_det[0]['contact_name'] or ''
			ret['contact_no']		 = contact_det and contact_det[0]['contact_no'] or ''
			ret['email_id']			 = contact_det and contact_det[0]['email_id'] or ''
		
			return ret
		else:
			msgprint("Customer : %s does not exist in system." % (name))
			raise Exception
		

	# ====================================================================================================================		
	def get_contact_details(self, arg):
		arg = eval(arg)
		contact = sql("select contact_no, email_id from `tabContact` where contact_name = '%s' and customer_name = '%s'" %(arg['contact_person'],arg['customer']), as_dict = 1)
		ret = {
			'contact_no' : contact and contact[0]['contact_no'] or '',
			'email_id' : contact and contact[0]['email_id'] or ''
		}
		return ret
		
	# ====================================================================================================================
	def on_update(self):
		# Add to calendar
		#if self.doc.contact_date and self.doc.last_contact_date != self.doc.contact_date:
		if self.doc.contact_date and self.doc.contact_date_ref != self.doc.contact_date:
			if self.doc.contact_by:
				self.add_calendar_event()
			set(self.doc, 'contact_date_ref',self.doc.contact_date)
		set(self.doc, 'status', 'Draft')
	
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
		desc = desc+ '. By : ' + cstr(self.doc.contact_by)
		
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

	#--------------Validation For Last Contact Date-----------------
	# ====================================================================================================================
	def set_last_contact_date(self):
		if self.doc.contact_date_ref and self.doc.contact_date_ref != self.doc.contact_date:
			if getdate(self.doc.contact_date_ref) < getdate(self.doc.contact_date):
				self.doc.last_contact_date=self.doc.contact_date_ref
			else:
				msgprint("Contact Date Cannot be before Last Contact Date")
				raise Exception
	
	# check if item present in item table
	# ====================================================================================================================
	def validate_item_details(self):
		if not getlist(self.doclist, 'enquiry_details'):
			msgprint("Please select items for which enquiry needs to be made")
			raise Exception
	
	#check if enquiry date in the range of fiscal year selected
	#=====================================================
	def validate_fiscal_year(self):
		fy=sql("select year_start_date from `tabFiscal Year` where name='%s'"%self.doc.fiscal_year)
		ysd=fy and fy[0][0] or ""
		yed=add_days(str(ysd),365)
		if str(self.doc.transaction_date) < str(ysd) or str(self.doc.transaction_date) > str(yed):
			msgprint("Opportunity Date is not within the Fiscal Year selected")
			raise Exception		

	def validate_lead_cust(self):
		if self.doc.enquiry_from == 'Lead' and not self.doc.lead:
			msgprint("Lead Id is mandatory if 'Opportunity From' is selected as Lead", raise_exception=1)
		elif self.doc.enquiry_from == 'Customer' and not self.doc.customer:
			msgprint("Customer is mandatory if 'Opportunity From' is selected as Customer", raise_exception=1)

	
	def validate(self):
		self.validate_fiscal_year()
		self.set_last_contact_date()
		self.validate_item_details()
		self.validate_lead_cust()
		
	# On Submit Functions
	# ====================================================================================================================
	def on_submit(self):
		set(self.doc, 'status', 'Submitted')
		
	# ====================================================================================================================	
	def on_cancel(self):
		chk = sql("select t1.name from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.docstatus=1 and (t1.status!='Order Lost' and t1.status!='Cancelled') and t2.prevdoc_docname = %s",self.doc.name)
		if chk:
			msgprint("Quotation No. "+cstr(chk[0][0])+" is submitted against this Opportunity. Thus can not be cancelled.")
			raise Exception
		else:
			set(self.doc, 'status', 'Cancelled')
		
	# declare as enquiry lost
	#---------------------------
	def declare_enquiry_lost(self,arg):
		chk = sql("select t1.name from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.docstatus=1 and (t1.status!='Order Lost' and t1.status!='Cancelled') and t2.prevdoc_docname = %s",self.doc.name)
		if chk:
			msgprint("Quotation No. "+cstr(chk[0][0])+" is submitted against this Opportunity. Thus 'Opportunity Lost' can not be declared against it.")
			raise Exception
		else:
			set(self.doc, 'status', 'Opportunity Lost')
			set(self.doc, 'order_lost_reason', arg)
			return 'true'
					
	#---------------------- Add details in follow up table----------------
	# ====================================================================================================================
	def add_in_follow_up(self,message,type):
		import datetime
		child = addchild( self.doc, 'follow_up', 'Communication Log', 1, self.doclist)
		child.date = datetime.datetime.now().date().strftime('%Y-%m-%d')
		child.notes = message
		child.follow_up_type = type
		child.save()

	#-------------------SMS----------------------------------------------
	# ====================================================================================================================
	def send_sms(self):
		if not self.doc.sms_message:
			msgprint("Please enter message in SMS Section ")
			raise Exception
		elif not getlist(self.doclist, 'enquiry_sms_detail'):
			msgprint("Please mention mobile no. to which sms needs to be sent")
			raise Exception
		else:
			receiver_list = []
			for d in getlist(self.doclist,'enquiry_sms_detail'):
				if d.other_mobile_no:
					receiver_list.append(d.other_mobile_no)
		
		if receiver_list:
			msgprint(get_obj('SMS Control', 'SMS Control').send_sms(receiver_list, self.doc.sms_message))
			self.add_in_follow_up(self.doc.sms_message,'SMS')
