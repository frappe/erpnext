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

from webnotes.utils import add_days, cstr, getdate, cint
from webnotes.model.bean import getlist
from webnotes import msgprint

sql = webnotes.conn.sql
	
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.fname = 'enq_details'
		self.tname = 'Opportunity Item'

		self._prev = webnotes._dict({
			"contact_date": webnotes.conn.get_value("Opportunity", self.doc.name, "contact_date") if \
				(not cint(self.doc.fields.get("__islocal"))) else None,
			"contact_by": webnotes.conn.get_value("Opportunity", self.doc.name, "contact_by") if \
				(not cint(self.doc.fields.get("__islocal"))) else None,
		})

	def onload(self):
		self.add_communication_list()
		
	def get_item_details(self, item_code):
		item = sql("""select item_name, stock_uom, description_html, description, item_group, brand
			from `tabItem` where name = %s""", item_code, as_dict=1)
		ret = {
			'item_name': item and item[0]['item_name'] or '',
			'uom': item and item[0]['stock_uom'] or '',
			'description': item and item[0]['description_html'] or item[0]['description'] or '',
			'item_group': item and item[0]['item_group'] or '',
			'brand': item and item[0]['brand'] or ''
		}
		return ret

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
			
	def get_contact_details(self, arg):
		arg = eval(arg)
		contact = sql("select contact_no, email_id from `tabContact` where contact_name = '%s' and customer_name = '%s'" %(arg['contact_person'],arg['customer']), as_dict = 1)
		ret = {
			'contact_no' : contact and contact[0]['contact_no'] or '',
			'email_id' : contact and contact[0]['email_id'] or ''
		}
		return ret
		
	def on_update(self):
		# Add to calendar
		if self.doc.contact_date and self.doc.contact_date_ref != self.doc.contact_date:
			webnotes.conn.set(self.doc, 'contact_date_ref',self.doc.contact_date)

		self.add_calendar_event()

	def add_calendar_event(self, opts=None, force=False):
		if not opts:
			opts = webnotes._dict()
		
		opts.description = ""
		
		if self.doc.customer:
			if self.doc.contact_person:
				opts.description = 'Contact '+cstr(self.doc.contact_person)
			else:
				opts.description = 'Contact customer '+cstr(self.doc.customer)
		elif self.doc.lead:
			if self.doc.contact_display:
				opts.description = 'Contact '+cstr(self.doc.contact_display)
			else:
				opts.description = 'Contact lead '+cstr(self.doc.lead)
				
		opts.subject = opts.description
		opts.description += '. By : ' + cstr(self.doc.contact_by)
		
		if self.doc.to_discuss:
			opts.description += ' To Discuss : ' + cstr(self.doc.to_discuss)
		
		super(DocType, self).add_calendar_event(opts, force)

	def set_last_contact_date(self):
		if self.doc.contact_date_ref and self.doc.contact_date_ref != self.doc.contact_date:
			if getdate(self.doc.contact_date_ref) < getdate(self.doc.contact_date):
				self.doc.last_contact_date=self.doc.contact_date_ref
			else:
				msgprint("Contact Date Cannot be before Last Contact Date")
				raise Exception

	def validate_item_details(self):
		if not getlist(self.doclist, 'enquiry_details'):
			msgprint("Please select items for which enquiry needs to be made")
			raise Exception

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
		
		if not self.doc.status:
			self.doc.status = "Draft"

	def on_submit(self):
		webnotes.conn.set(self.doc, 'status', 'Submitted')
	
	def on_cancel(self):
		chk = sql("select t1.name from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.docstatus=1 and (t1.status!='Order Lost' and t1.status!='Cancelled') and t2.prevdoc_docname = %s",self.doc.name)
		if chk:
			msgprint("Quotation No. "+cstr(chk[0][0])+" is submitted against this Opportunity. Thus can not be cancelled.")
			raise Exception
		else:
			webnotes.conn.set(self.doc, 'status', 'Cancelled')
		
	def declare_enquiry_lost(self,arg):
		chk = sql("select t1.name from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.docstatus=1 and (t1.status!='Order Lost' and t1.status!='Cancelled') and t2.prevdoc_docname = %s",self.doc.name)
		if chk:
			msgprint("Quotation No. "+cstr(chk[0][0])+" is submitted against this Opportunity. Thus 'Opportunity Lost' can not be declared against it.")
			raise Exception
		else:
			webnotes.conn.set(self.doc, 'status', 'Opportunity Lost')
			webnotes.conn.set(self.doc, 'order_lost_reason', arg)
			return 'true'

	def on_trash(self):
		self.delete_events()