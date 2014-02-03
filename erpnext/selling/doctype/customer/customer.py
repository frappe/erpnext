# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr
from webnotes.model.doc import Document, make_autoname
from webnotes import msgprint, _
import webnotes.defaults


from erpnext.utilities.transaction_base import TransactionBase
from erpnext.utilities.doctype.address.address import get_address_display
from erpnext.utilities.doctype.contact.contact import get_contact_details
from erpnext.accounts.party import create_party_account

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
				
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
	
	def validate_values(self):
		if webnotes.defaults.get_global_default('cust_master_name') == 'Naming Series' and not self.doc.naming_series:
			webnotes.throw("Series is Mandatory.", webnotes.MandatoryError)

	def validate(self):
		self.validate_values()

	def update_lead_status(self):
		if self.doc.lead_name:
			webnotes.conn.sql("update `tabLead` set status='Converted' where name = %s", self.doc.lead_name)

	def update_address(self):
		webnotes.conn.sql("""update `tabAddress` set customer_name=%s, modified=NOW() 
			where customer=%s""", (self.doc.customer_name, self.doc.name))

	def update_contact(self):
		webnotes.conn.sql("""update `tabContact` set customer_name=%s, modified=NOW() 
			where customer=%s""", (self.doc.customer_name, self.doc.name))

	def update_credit_days_limit(self):
		webnotes.conn.sql("""update tabAccount set credit_days = %s, credit_limit = %s 
			where master_type='Customer' and master_name = %s""", 
			(self.doc.credit_days or 0, self.doc.credit_limit or 0, self.doc.name))

	def create_lead_address_contact(self):
		if self.doc.lead_name:
			if not webnotes.conn.get_value("Address", {"lead": self.doc.lead_name, "customer": self.doc.customer}):
				webnotes.conn.sql("""update `tabAddress` set customer=%s, customer_name=%s where lead=%s""", 
					(self.doc.name, self.doc.customer_name, self.doc.lead_name))

			lead = webnotes.conn.get_value("Lead", self.doc.lead_name, ["lead_name", "email_id", "phone", "mobile_no"], as_dict=True)
			c = Document('Contact') 
			c.first_name = lead.lead_name 
			c.email_id = lead.email_id
			c.phone = lead.phone
			c.mobile_no = lead.mobile_no
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
		self.update_address()
		self.update_contact()

		# create account head
		create_party_account(self.doc.name, "Customer", self.doc.company)

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
		addresses = webnotes.conn.sql("""select name, lead from `tabAddress`
			where customer=%s""", (self.doc.name,))
		
		for name, lead in addresses:
			if lead:
				webnotes.conn.sql("""update `tabAddress` set customer=null, customer_name=null
					where name=%s""", name)
			else:
				webnotes.conn.sql("""delete from `tabAddress` where name=%s""", name)
	
	def delete_customer_contact(self):
		for contact in webnotes.conn.sql_list("""select name from `tabContact` 
			where customer=%s""", self.doc.name):
				webnotes.delete_doc("Contact", contact)
	
	def delete_customer_account(self):
		"""delete customer's ledger if exist and check balance before deletion"""
		acc = webnotes.conn.sql("select name from `tabAccount` where master_type = 'Customer' \
			and master_name = %s and docstatus < 2", self.doc.name)
		if acc:
			webnotes.delete_doc('Account', acc[0][0])

	def on_trash(self):
		self.delete_customer_address()
		self.delete_customer_contact()
		self.delete_customer_account()
		if self.doc.lead_name:
			webnotes.conn.sql("update `tabLead` set status='Interested' where name=%s",self.doc.lead_name)
			
	def before_rename(self, olddn, newdn, merge=False):
		from erpnext.accounts.utils import rename_account_for
		rename_account_for("Customer", olddn, newdn, merge)

	def after_rename(self, olddn, newdn, merge=False):
		set_field = ''
		if webnotes.defaults.get_global_default('cust_master_name') == 'Customer Name':
			webnotes.conn.set(self.doc, "customer_name", newdn)
			self.update_contact()
			set_field = ", customer_name=%(newdn)s"
		self.update_customer_address(newdn, set_field)

	def update_customer_address(self, newdn, set_field):
		webnotes.conn.sql("""update `tabAddress` set address_title=%(newdn)s 
			{set_field} where customer=%(newdn)s"""\
			.format(set_field=set_field), ({"newdn": newdn}))

@webnotes.whitelist()
def get_dashboard_info(customer):
	if not webnotes.has_permission("Customer", "read", customer):
		webnotes.msgprint("No Permission", raise_exception=True)
	
	out = {}
	for doctype in ["Opportunity", "Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
		out[doctype] = webnotes.conn.get_value(doctype, 
			{"customer": customer, "docstatus": ["!=", 2] }, "count(*)")
	
	billing = webnotes.conn.sql("""select sum(grand_total), sum(outstanding_amount) 
		from `tabSales Invoice` 
		where customer=%s 
			and docstatus = 1
			and fiscal_year = %s""", (customer, webnotes.conn.get_default("fiscal_year")))
	
	out["total_billing"] = billing[0][0]
	out["total_unpaid"] = billing[0][1]
	
	return out

@webnotes.whitelist()
def get_customer_details(customer, price_list=None, currency=None):
	if not webnotes.has_permission("Customer", "read", customer):
		webnotes.throw("Not Permitted", webnotes.PermissionError)
		
	out = {}
	customer_bean = webnotes.bean("Customer", customer)
	customer = customer_bean.doc

	out = webnotes._dict({
		"customer_address": webnotes.conn.get_value("Address", 
			{"customer": customer.name, "is_primary_address":1}, "name"),
		"contact_person": webnotes.conn.get_value("Contact", 
			{"customer":customer.name, "is_primary_contact":1}, "name")
	})

	# address display
	out.address_display = get_address_display(out.customer_address)
	
	# primary contact details
	out.update(get_contact_details(out.contact_person))

	# copy
	for f in ['customer_name', 'customer_group', 'territory']:
		out[f] = customer.get(f)
	
	# fields prepended with default in Customer doctype
	for f in ['sales_partner', 'commission_rate', 'currency', 'price_list']:
		if customer.get("default_" + f):
			out[f] = customer.get("default_" + f)

	# price list
	from webnotes.defaults import get_defaults_for
	out.selling_price_list = get_defaults_for(webnotes.session.user).get(price_list)
	if isinstance(out.selling_price_list, list):
		out.selling_price_list = None
	
	out.selling_price_list = out.selling_price_list or customer.price_list \
		or webnotes.conn.get_value("Customer Group", 
			customer.customer_group, "default_price_list") or price_list
	
	if out.selling_price_list:
		out.price_list_currency = webnotes.conn.get_value("Price List", out.selling_price_list, "currency")
	
	if not out.currency:
		out.currency = currency
	
	# sales team
	out.sales_team = [{
		"sales_person": d.sales_person, 
		"sales_designation": d.sales_designation
	} for d in customer_bean.doclist.get({"doctype":"Sales Team"})]
	
	return out