# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.doc import Document, make_autoname
from frappe import msgprint, _
import frappe.defaults


from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import create_party_account

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
				
	def autoname(self):
		cust_master_name = frappe.defaults.get_global_default('cust_master_name')
		if cust_master_name == 'Customer Name':
			if frappe.db.exists("Supplier", self.doc.customer_name):
				msgprint(_("A Supplier exists with same name"), raise_exception=1)
			self.doc.name = self.doc.customer_name
		else:
			self.doc.name = make_autoname(self.doc.naming_series+'.#####')

	def get_company_abbr(self):
		return frappe.db.get_value('Company', self.doc.company, 'abbr')
	
	def validate_values(self):
		if frappe.defaults.get_global_default('cust_master_name') == 'Naming Series' and not self.doc.naming_series:
			frappe.throw("Series is Mandatory.", frappe.MandatoryError)

	def validate(self):
		self.validate_values()

	def update_lead_status(self):
		if self.doc.lead_name:
			frappe.db.sql("update `tabLead` set status='Converted' where name = %s", self.doc.lead_name)

	def update_address(self):
		frappe.db.sql("""update `tabAddress` set customer_name=%s, modified=NOW() 
			where customer=%s""", (self.doc.customer_name, self.doc.name))

	def update_contact(self):
		frappe.db.sql("""update `tabContact` set customer_name=%s, modified=NOW() 
			where customer=%s""", (self.doc.customer_name, self.doc.name))

	def update_credit_days_limit(self):
		frappe.db.sql("""update tabAccount set credit_days = %s, credit_limit = %s 
			where master_type='Customer' and master_name = %s""", 
			(self.doc.credit_days or 0, self.doc.credit_limit or 0, self.doc.name))

	def create_lead_address_contact(self):
		if self.doc.lead_name:
			if not frappe.db.get_value("Address", {"lead": self.doc.lead_name, "customer": self.doc.customer}):
				frappe.db.sql("""update `tabAddress` set customer=%s, customer_name=%s where lead=%s""", 
					(self.doc.name, self.doc.customer_name, self.doc.lead_name))

			lead = frappe.db.get_value("Lead", self.doc.lead_name, ["lead_name", "email_id", "phone", "mobile_no"], as_dict=True)
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
		if frappe.db.exists("Customer Group", self.doc.name):
			frappe.msgprint("An Customer Group exists with same name (%s), \
				please change the Customer name or rename the Customer Group" % 
				self.doc.name, raise_exception=1)

	def delete_customer_address(self):
		addresses = frappe.db.sql("""select name, lead from `tabAddress`
			where customer=%s""", (self.doc.name,))
		
		for name, lead in addresses:
			if lead:
				frappe.db.sql("""update `tabAddress` set customer=null, customer_name=null
					where name=%s""", name)
			else:
				frappe.db.sql("""delete from `tabAddress` where name=%s""", name)
	
	def delete_customer_contact(self):
		for contact in frappe.db.sql_list("""select name from `tabContact` 
			where customer=%s""", self.doc.name):
				frappe.delete_doc("Contact", contact)
	
	def delete_customer_account(self):
		"""delete customer's ledger if exist and check balance before deletion"""
		acc = frappe.db.sql("select name from `tabAccount` where master_type = 'Customer' \
			and master_name = %s and docstatus < 2", self.doc.name)
		if acc:
			frappe.delete_doc('Account', acc[0][0])

	def on_trash(self):
		self.delete_customer_address()
		self.delete_customer_contact()
		self.delete_customer_account()
		if self.doc.lead_name:
			frappe.db.sql("update `tabLead` set status='Interested' where name=%s",self.doc.lead_name)
			
	def before_rename(self, olddn, newdn, merge=False):
		from erpnext.accounts.utils import rename_account_for
		rename_account_for("Customer", olddn, newdn, merge, self.doc.company)

	def after_rename(self, olddn, newdn, merge=False):
		set_field = ''
		if frappe.defaults.get_global_default('cust_master_name') == 'Customer Name':
			frappe.db.set(self.doc, "customer_name", newdn)
			self.update_contact()
			set_field = ", customer_name=%(newdn)s"
		self.update_customer_address(newdn, set_field)

	def update_customer_address(self, newdn, set_field):
		frappe.db.sql("""update `tabAddress` set address_title=%(newdn)s 
			{set_field} where customer=%(newdn)s"""\
			.format(set_field=set_field), ({"newdn": newdn}))

@frappe.whitelist()
def get_dashboard_info(customer):
	if not frappe.has_permission("Customer", "read", customer):
		frappe.msgprint("No Permission", raise_exception=True)
	
	out = {}
	for doctype in ["Opportunity", "Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
		out[doctype] = frappe.db.get_value(doctype, 
			{"customer": customer, "docstatus": ["!=", 2] }, "count(*)")
	
	billing = frappe.db.sql("""select sum(grand_total), sum(outstanding_amount) 
		from `tabSales Invoice` 
		where customer=%s 
			and docstatus = 1
			and fiscal_year = %s""", (customer, frappe.db.get_default("fiscal_year")))
	
	out["total_billing"] = billing[0][0]
	out["total_unpaid"] = billing[0][1]
	
	return out


def get_customer_list(doctype, txt, searchfield, start, page_len, filters):
	if frappe.db.get_default("cust_master_name") == "Customer Name":
		fields = ["name", "customer_group", "territory"]
	else:
		fields = ["name", "customer_name", "customer_group", "territory"]
		
	return frappe.db.sql("""select %s from `tabCustomer` where docstatus < 2 
		and (%s like %s or customer_name like %s) order by 
		case when name like %s then 0 else 1 end,
		case when customer_name like %s then 0 else 1 end,
		name, customer_name limit %s, %s""" % 
		(", ".join(fields), searchfield, "%s", "%s", "%s", "%s", "%s", "%s"), 
		("%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, start, page_len))