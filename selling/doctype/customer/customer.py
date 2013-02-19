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

from webnotes.utils import cstr
from webnotes.model.doc import Document, make_autoname
from webnotes import msgprint, _
import webnotes.defaults

sql = webnotes.conn.sql

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def onload(self):
		self.add_communication_list()
			
	def autoname(self):
		cust_master_name = webnotes.defaults.get_global_default('cust_master_name')
		if cust_master_name == 'Customer Name':
			if webnotes.conn.exists("Supplier", self.doc.customer_name):
				msgprint(_("A Supplier exists with same name"), raise_exception=1)
			self.doc.name = self.doc.customer_name
		else:
			self.doc.name = make_autoname(self.doc.naming_series+'.#####')

	def get_company_abbr(self):
		return webnotes.conn.get_value('Company', self.doc.company, 'abbr')

	def get_receivables_group(self):
		g = sql("select receivables_group from tabCompany where name=%s", self.doc.company)
		g = g and g[0][0] or '' 
		if not g:
			msgprint("Update Company master, assign a default group for Receivables")
			raise Exception
		return g
	
	def validate_values(self):
		if webnotes.defaults.get_global_default('cust_master_name') == 'Naming Series' and not self.doc.naming_series:
			msgprint("Series is Mandatory.")
			raise Exception

	def validate(self):
		self.validate_values()

	def create_customer_address(self):
		addr_flds = [self.doc.address_line1, self.doc.address_line2, self.doc.city, self.doc.state, self.doc.country, self.doc.pincode]
		address_line = "\n".join(filter(lambda x : (x!='' and x!=None),addr_flds))

		if self.doc.phone_1:
			address_line = address_line + "\n" + "Phone: " + cstr(self.doc.phone_1)
		if self.doc.email_id:
			address_line = address_line + "\n" + "E-mail: " + cstr(self.doc.email_id)
		webnotes.conn.set(self.doc,'address', address_line)
		
		telephone = "(O): " + cstr(self.doc.phone_1) +"\n"+ cstr(self.doc.phone_2) + "\n" + "(M): " +	"\n" + "(fax): " + cstr(self.doc.fax_1)
		webnotes.conn.set(self.doc,'telephone',telephone)

	def create_p_contact(self,nm,phn_no,email_id,mob_no,fax,cont_addr):
		c1 = Document('Contact')
		c1.first_name = nm
		c1.contact_name = nm
		c1.contact_no = phn_no
		c1.email_id = email_id
		c1.mobile_no = mob_no
		c1.fax = fax
		c1.contact_address = cont_addr
		c1.is_primary_contact = 'Yes'
		c1.is_customer =1
		c1.customer = self.doc.name
		c1.customer_name = self.doc.customer_name
		c1.customer_address = self.doc.address
		c1.customer_group = self.doc.customer_group
		c1.save(1)

	def create_customer_contact(self):
		contact = sql("select distinct name from `tabContact` where customer_name=%s", (self.doc.customer_name))
		contact = contact and contact[0][0] or ''
		if not contact:
			# create primary contact for individual customer 
			if self.doc.customer_type == 'Individual':
				self.create_p_contact(self.doc.customer_name,self.doc.phone_1,self.doc.email_id,'',self.doc.fax_1,self.doc.address)
		
			# create primary contact for lead
			elif self.doc.lead_name:
				c_detail = sql("select lead_name, company_name, contact_no, mobile_no, email_id, fax, address from `tabLead` where name =%s", self.doc.lead_name, as_dict=1)
				self.create_p_contact(c_detail and c_detail[0]['lead_name'] or '', c_detail and c_detail[0]['contact_no'] or '', c_detail and c_detail[0]['email_id'] or '', c_detail and c_detail[0]['mobile_no'] or '', c_detail and c_detail[0]['fax'] or '', c_detail and c_detail[0]['address'] or '')

	def update_lead_status(self):
		if self.doc.lead_name:
			sql("update `tabLead` set status='Converted' where name = %s", self.doc.lead_name)

	def create_account_head(self):
		if self.doc.company :
			abbr = self.get_company_abbr()
			if not webnotes.conn.exists("Account", (self.doc.name + " - " + abbr)):
				parent_account = self.get_receivables_group()
				# create
				from accounts.utils import add_ac
				ac = add_ac({
					'account_name':self.doc.name,
					'parent_account': parent_account, 
					'group_or_ledger':'Ledger',
					'company':self.doc.company, 
					'account_type':'', 
					'tax_rate':'0', 
					'master_type':'Customer', 
					'master_name':self.doc.name
				})
				msgprint("Account Head: %s created" % ac)
		else :
			msgprint("Please Select Company under which you want to create account head")

	def update_credit_days_limit(self):
		sql("""update tabAccount set credit_days = %s, credit_limit = %s 
			where name = %s""", (self.doc.credit_days or 0, self.doc.credit_limit or 0, 
				self.doc.name + " - " + self.get_company_abbr()))

	def create_lead_address_contact(self):
		if self.doc.lead_name:
			details = sql("select name, lead_name, address_line1, address_line2, city, country, state, pincode, phone, mobile_no, fax, email_id from `tabLead` where name = '%s'" %(self.doc.lead_name), as_dict = 1)
			d = Document('Address') 
			d.address_line1 = details[0]['address_line1'] 
			d.address_line2 = details[0]['address_line2']
			d.city = details[0]['city']
			d.country = details[0]['country']
			d.pincode = details[0]['pincode']
			d.state = details[0]['state']
			d.fax = details[0]['fax']
			d.email_id = details[0]['email_id']
			d.phone = details[0]['phone']
			d.customer = self.doc.name
			d.customer_name = self.doc.customer_name
			d.is_primary_address = 1
			d.address_type = 'Office'
			try:
				d.save(1)
			except NameError, e:
				pass
				
			c = Document('Contact') 
			c.first_name = details[0]['lead_name'] 
			c.email_id = details[0]['email_id']
			c.phone = details[0]['phone']
			c.mobile_no = details[0]['mobile_no']
			c.customer = self.doc.name
			c.customer_name = self.doc.customer_name
			c.is_primary_contact = 1
			try:
				c.save(1)
			except NameError, e:
				pass

	def on_update(self):
		self.validate_name_with_customer_group()
		
		self.update_lead_status()
		# create account head
		self.create_account_head()
		# update credit days and limit in account
		self.update_credit_days_limit()
		#create address and contact from lead
		self.create_lead_address_contact()
		
	def validate_name_with_customer_group(self):
		if webnotes.conn.exists("Customer Group", self.doc.name):
			webnotes.msgprint("An Customer Group exists with same name (%s), \
				please change the Customer name or rename the Customer Group" % 
				self.doc.name, raise_exception=1)

	def delete_customer_address(self):
		for rec in sql("select * from `tabAddress` where customer='%s'" %(self.doc.name), as_dict=1):
			sql("delete from `tabAddress` where name=%s",(rec['name']))
	
	def delete_customer_contact(self):
		for rec in sql("select * from `tabContact` where customer='%s'" %(self.doc.name), as_dict=1):
			sql("delete from `tabContact` where name=%s",(rec['name']))
	
	def delete_customer_communication(self):
		webnotes.conn.sql("""\
			delete from `tabCommunication`
			where customer = %s and supplier is null""", self.doc.name)
			
	def delete_customer_account(self):
		"""delete customer's ledger if exist and check balance before deletion"""
		acc = sql("select name from `tabAccount` where master_type = 'Customer' \
			and master_name = %s and docstatus < 2", self.doc.name)
		if acc:
			from webnotes.model import delete_doc
			delete_doc('Account', acc[0][0])

	def on_trash(self):
		self.delete_customer_address()
		self.delete_customer_contact()
		self.delete_customer_communication()
		self.delete_customer_account()
		if self.doc.lead_name:
			sql("update `tabLead` set status='Interested' where name=%s",self.doc.lead_name)
			
	def on_rename(self, new, old):
		#update customer_name if not naming series
		if webnotes.defaults.get_global_default('cust_master_name') == 'Customer Name':
			update_fields = [
			('Customer', 'name'),
			('Address', 'customer'),
			('Contact', 'customer'),
			('Customer Issue', 'customer'),
			('Delivery Note', 'customer'),
			('Opportunity', 'customer'),
			('Installation Note', 'customer'),
			('Maintenance Schedule', 'customer'),
			('Maintenance Visit', 'customer'),
			('Project', 'customer'),
			('Quotation', 'customer'),
			('Sales Invoice', 'customer'),
			('Sales Order', 'customer'),
			('Serial No', 'customer'),
			('Shipping Address', 'customer'),
			('Stock Entry', 'customer'),
			('Support Ticket', 'customer'),
			('Task', 'customer')]
			for rec in update_fields:
				sql("""update `tab%s` set customer_name = %s
					where `%s` = %s""" % (rec[0], "%s" ,rec[1], "%s"), (new, old))
		
		for account in webnotes.conn.sql("""select name, account_name from 
			tabAccount where master_name=%s and master_type='Customer'""", old, as_dict=1):
			if account.account_name != new:
				webnotes.rename_doc("Account", account.name, new)

		#update master_name in doctype account
		webnotes.conn.sql("""update `tabAccount` set master_name = %s, 
			master_type = 'Customer' where master_name = %s""", (new,old))