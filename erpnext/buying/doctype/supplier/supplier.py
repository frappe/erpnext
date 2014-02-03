# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
import webnotes.defaults

from webnotes.utils import cint
from webnotes import msgprint, _
from webnotes.model.doc import make_autoname
from erpnext.accounts.party import create_party_account

from erpnext.utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		supp_master_name = webnotes.defaults.get_global_default('supp_master_name')
		
		if supp_master_name == 'Supplier Name':
			if webnotes.conn.exists("Customer", self.doc.supplier_name):
				webnotes.msgprint(_("A Customer exists with same name"), raise_exception=1)
			self.doc.name = self.doc.supplier_name
		else:
			self.doc.name = make_autoname(self.doc.naming_series + '.#####')

	def update_address(self):
		webnotes.conn.sql("""update `tabAddress` set supplier_name=%s, modified=NOW() 
			where supplier=%s""", (self.doc.supplier_name, self.doc.name))

	def update_contact(self):
		webnotes.conn.sql("""update `tabContact` set supplier_name=%s, modified=NOW() 
			where supplier=%s""", (self.doc.supplier_name, self.doc.name))

	def update_credit_days_limit(self):
		webnotes.conn.sql("""update tabAccount set credit_days = %s where name = %s""", 
			(cint(self.doc.credit_days), self.doc.name + " - " + self.get_company_abbr()))

	def on_update(self):
		if not self.doc.naming_series:
			self.doc.naming_series = ''

		self.update_address()
		self.update_contact()

		# create account head
		create_party_account(self.doc.name, "Supplier", self.doc.company)

		# update credit days and limit in account
		self.update_credit_days_limit()
		
	def get_company_abbr(self):
		return webnotes.conn.sql("select abbr from tabCompany where name=%s", self.doc.company)[0][0]
	
	def validate(self):
		#validation for Naming Series mandatory field...
		if webnotes.defaults.get_global_default('supp_master_name') == 'Naming Series':
			if not self.doc.naming_series:
				msgprint("Series is Mandatory.", raise_exception=1)
			
	def get_contacts(self,nm):
		if nm:
			contact_details =webnotes.conn.convert_to_lists(webnotes.conn.sql("select name, CONCAT(IFNULL(first_name,''),' ',IFNULL(last_name,'')),contact_no,email_id from `tabContact` where supplier = '%s'"%nm))
	 
			return contact_details
		else:
			return ''
			
	def delete_supplier_address(self):
		for rec in webnotes.conn.sql("select * from `tabAddress` where supplier=%s", (self.doc.name,), as_dict=1):
			webnotes.conn.sql("delete from `tabAddress` where name=%s",(rec['name']))
	
	def delete_supplier_contact(self):
		for contact in webnotes.conn.sql_list("""select name from `tabContact` 
			where supplier=%s""", self.doc.name):
				webnotes.delete_doc("Contact", contact)
	
	def delete_supplier_account(self):
		"""delete supplier's ledger if exist and check balance before deletion"""
		acc = webnotes.conn.sql("select name from `tabAccount` where master_type = 'Supplier' \
			and master_name = %s and docstatus < 2", self.doc.name)
		if acc:
			webnotes.delete_doc('Account', acc[0][0])
			
	def on_trash(self):
		self.delete_supplier_address()
		self.delete_supplier_contact()
		self.delete_supplier_account()
		
	def before_rename(self, olddn, newdn, merge=False):
		from erpnext.accounts.utils import rename_account_for
		rename_account_for("Supplier", olddn, newdn, merge)

	def after_rename(self, olddn, newdn, merge=False):
		set_field = ''
		if webnotes.defaults.get_global_default('supp_master_name') == 'Supplier Name':
			webnotes.conn.set(self.doc, "supplier_name", newdn)
			self.update_contact()
			set_field = ", supplier_name=%(newdn)s"
		self.update_supplier_address(newdn, set_field)

	def update_supplier_address(self, newdn, set_field):
		webnotes.conn.sql("""update `tabAddress` set address_title=%(newdn)s 
			{set_field} where supplier=%(newdn)s"""\
			.format(set_field=set_field), ({"newdn": newdn}))

@webnotes.whitelist()
def get_dashboard_info(supplier):
	if not webnotes.has_permission("Supplier", "read", supplier):
		webnotes.msgprint("No Permission", raise_exception=True)
	
	out = {}
	for doctype in ["Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"]:
		out[doctype] = webnotes.conn.get_value(doctype, 
			{"supplier": supplier, "docstatus": ["!=", 2] }, "count(*)")
	
	billing = webnotes.conn.sql("""select sum(grand_total), sum(outstanding_amount) 
		from `tabPurchase Invoice` 
		where supplier=%s 
			and docstatus = 1
			and fiscal_year = %s""", (supplier, webnotes.conn.get_default("fiscal_year")))
	
	out["total_billing"] = billing[0][0]
	out["total_unpaid"] = billing[0][1]
	
	return out
	
@webnotes.whitelist()
def get_supplier_details(supplier, price_list=None, currency=None):
	if not webnotes.has_permission("Supplier", "read", supplier):
		webnotes.msgprint("No Permission", raise_exception=webnotes.PermissionError)

	supplier = webnotes.doc("Supplier", supplier)
	
	out = webnotes._dict({
		"supplier_address": webnotes.conn.get_value("Address", 
			{"supplier": supplier.name, "is_primary_address":1}, "name"),
		"contact_person": webnotes.conn.get_value("Contact", 
			{"supplier":supplier.name, "is_primary_contact":1}, "name")
	})

	for f in ['currency', 'taxes_and_charges']:
		if supplier.fields.get("default_" + f):
			out[f] = supplier.fields.get("default_" + f)
	
	out.supplier_name = supplier.supplier_name
	out.currency = supplier.default_currency or currency
	out.buying_price_list = supplier.default_price_list or price_list
		
	return out