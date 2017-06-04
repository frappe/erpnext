# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.naming import make_autoname
from frappe import _, msgprint, throw
import frappe.defaults
from frappe.utils import flt, cint, cstr
from frappe.desk.reportview import build_match_conditions
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.utilities.address_and_contact import load_address_and_contact
from erpnext.accounts.party import validate_party_accounts, get_timeline_data # keep this
from erpnext.accounts.party_status import get_party_status
from erpnext import get_default_currency

class Customer(TransactionBase):
	def get_feed(self):
		return self.customer_name

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self, "customer")
		self.load_dashboard_info()

	def load_dashboard_info(self):
		billing_this_year = frappe.db.sql("""
			select sum(debit_in_account_currency) - sum(credit_in_account_currency), account_currency
			from `tabGL Entry`
			where voucher_type='Sales Invoice' and party_type = 'Customer'
				and party=%s and fiscal_year = %s""",
			(self.name, frappe.db.get_default("fiscal_year")))

		total_unpaid = frappe.db.sql("""select sum(outstanding_amount)
			from `tabSales Invoice`
			where customer=%s and docstatus = 1""", self.name)

		info = {}
		info["billing_this_year"] = billing_this_year[0][0] if billing_this_year else 0
		info["currency"] = billing_this_year[0][1] if billing_this_year else get_default_currency()
		info["total_unpaid"] = total_unpaid[0][0] if total_unpaid else 0

		self.set_onload('dashboard_info', info)


	def autoname(self):
		cust_master_name = frappe.defaults.get_global_default('cust_master_name')
		if cust_master_name == 'Customer Name':
			self.name = self.get_customer_name()
		else:
			if not self.naming_series:
				frappe.throw(_("Series is mandatory"), frappe.MandatoryError)

			self.name = make_autoname(self.naming_series+'.#####')

	def get_customer_name(self):
		if frappe.db.get_value("Customer", self.customer_name):
			count = frappe.db.sql("""select ifnull(MAX(CAST(SUBSTRING_INDEX(name, ' ', -1) AS UNSIGNED)), 0) from tabCustomer
				 where name like %s""", "%{0} - %".format(self.customer_name), as_list=1)[0][0]
			count = cint(count) + 1
			return "{0} - {1}".format(self.customer_name, cstr(count))

		return self.customer_name

	def after_insert(self):
		'''If customer created from Lead, update customer id in quotations, opportunities'''
		self.update_lead_status()

	def validate(self):
		self.flags.is_new_doc = self.is_new()
		self.flags.old_lead = self.lead_name
		validate_party_accounts(self)
		self.status = get_party_status(self)
		self.validate_credit_limit_on_change()

	def on_update(self):
		self.validate_name_with_customer_group()

		if self.flags.old_lead != self.lead_name:
			self.update_lead_status()

		self.update_address()
		self.update_contact()

		if self.flags.is_new_doc:
			self.create_lead_address_contact()

	def update_lead_status(self):
		'''If Customer created from Lead, update lead status to "Converted"
		update Customer link in Quotation, Opportunity'''
		if self.lead_name:
		 	frappe.db.set_value('Lead', self.lead_name, 'status', 'Converted', update_modified=False)

			for doctype in ('Opportunity', 'Quotation'):
				for d in frappe.get_all(doctype, {'lead': self.lead_name}):
					frappe.db.set_value(doctype, d.name, 'customer', self.name, update_modified=False)

	def update_address(self):
		frappe.db.sql("""update `tabAddress` set customer_name=%s, modified=NOW()
			where customer=%s""", (self.customer_name, self.name))

	def update_contact(self):
		frappe.db.sql("""update `tabContact` set customer_name=%s, modified=NOW()
			where customer=%s""", (self.customer_name, self.name))

	def create_lead_address_contact(self):
		if self.lead_name:
			if not frappe.db.get_value("Address", {"lead": self.lead_name, "customer": self.name}):
				frappe.db.sql("""update `tabAddress` set customer=%s, customer_name=%s where lead=%s""",
					(self.name, self.customer_name, self.lead_name))

			lead = frappe.db.get_value("Lead", self.lead_name, ["lead_name", "email_id", "phone", "mobile_no"], as_dict=True)

			c = frappe.new_doc('Contact')
			c.first_name = lead.lead_name
			c.email_id = lead.email_id
			c.phone = lead.phone
			c.mobile_no = lead.mobile_no
			c.customer = self.name
			c.customer_name = self.customer_name
			c.is_primary_contact = 1
			c.flags.ignore_permissions = self.flags.ignore_permissions
			c.autoname()
			if not frappe.db.exists("Contact", c.name):
				c.insert()

	def validate_name_with_customer_group(self):
		if frappe.db.exists("Customer Group", self.name):
			frappe.throw(_("A Customer Group exists with same name please change the Customer name or rename the Customer Group"), frappe.NameError)

	def validate_credit_limit_on_change(self):
		if self.get("__islocal") or self.credit_limit == frappe.db.get_value("Customer", self.name, "credit_limit"):
			return

		for company in frappe.get_all("Company"):
			outstanding_amt = get_customer_outstanding(self.name, company.name)
			if flt(self.credit_limit) < outstanding_amt:
				frappe.throw(_("""New credit limit is less than current outstanding amount for the customer. Credit limit has to be atleast {0}""").format(outstanding_amt))

	def delete_customer_address(self):
		addresses = frappe.db.sql("""select name, lead from `tabAddress`
			where customer=%s""", (self.name,))

		for name, lead in addresses:
			if lead:
				frappe.db.sql("""update `tabAddress` set customer=null, customer_name=null
					where name=%s""", name)
			else:
				frappe.db.sql("""delete from `tabAddress` where name=%s""", name)

	def delete_customer_contact(self):
		for contact in frappe.db.sql_list("""select name from `tabContact`
			where customer=%s""", self.name):
				frappe.delete_doc("Contact", contact)

	def on_trash(self):
		self.delete_customer_address()
		self.delete_customer_contact()
		if self.lead_name:
			frappe.db.sql("update `tabLead` set status='Interested' where name=%s",self.lead_name)

	def after_rename(self, olddn, newdn, merge=False):
		set_field = ''
		if frappe.defaults.get_global_default('cust_master_name') == 'Customer Name':
			frappe.db.set(self, "customer_name", newdn)
			self.update_contact()
			set_field = ", customer_name=%(newdn)s"
		self.update_customer_address(newdn, set_field)

	def update_customer_address(self, newdn, set_field):
		frappe.db.sql("""update `tabAddress` set address_title=%(newdn)s
			{set_field} where customer=%(newdn)s"""\
			.format(set_field=set_field), ({"newdn": newdn}))


def get_customer_list(doctype, txt, searchfield, start, page_len, filters):
	if frappe.db.get_default("cust_master_name") == "Customer Name":
		fields = ["name", "customer_group", "territory"]
	else:
		fields = ["name", "customer_name", "customer_group", "territory"]

	match_conditions = build_match_conditions("Customer")
	match_conditions = "and {}".format(match_conditions) if match_conditions else ""

	return frappe.db.sql("""select %s from `tabCustomer` where docstatus < 2
		and (%s like %s or customer_name like %s)
		{match_conditions}
		order by
		case when name like %s then 0 else 1 end,
		case when customer_name like %s then 0 else 1 end,
		name, customer_name limit %s, %s""".format(match_conditions=match_conditions) %
		(", ".join(fields), searchfield, "%s", "%s", "%s", "%s", "%s", "%s"),
		("%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, start, page_len))


def check_credit_limit(customer, company):
	customer_outstanding = get_customer_outstanding(customer, company)

	credit_limit = get_credit_limit(customer, company)
	if credit_limit > 0 and flt(customer_outstanding) > credit_limit:
		msgprint(_("Credit limit has been crossed for customer {0} {1}/{2}")
			.format(customer, customer_outstanding, credit_limit))

		# If not authorized person raise exception
		credit_controller = frappe.db.get_value('Accounts Settings', None, 'credit_controller')
		if not credit_controller or credit_controller not in frappe.get_roles():
			throw(_("Please contact to the user who have Sales Master Manager {0} role")
				.format(" / " + credit_controller if credit_controller else ""))

def get_customer_outstanding(customer, company):
	# Outstanding based on GL Entries
	outstanding_based_on_gle = frappe.db.sql("""select sum(debit) - sum(credit)
		from `tabGL Entry` where party_type = 'Customer' and party = %s and company=%s""", (customer, company))

	outstanding_based_on_gle = flt(outstanding_based_on_gle[0][0]) if outstanding_based_on_gle else 0

	# Outstanding based on Sales Order
	outstanding_based_on_so = frappe.db.sql("""
		select sum(base_grand_total*(100 - per_billed)/100)
		from `tabSales Order`
		where customer=%s and docstatus = 1 and company=%s
		and per_billed < 100 and status != 'Closed'""", (customer, company))

	outstanding_based_on_so = flt(outstanding_based_on_so[0][0]) if outstanding_based_on_so else 0.0

	# Outstanding based on Delivery Note
	unmarked_delivery_note_items = frappe.db.sql("""select
			dn_item.name, dn_item.amount, dn.base_net_total, dn.base_grand_total
		from `tabDelivery Note` dn, `tabDelivery Note Item` dn_item
		where
			dn.name = dn_item.parent
			and dn.customer=%s and dn.company=%s
			and dn.docstatus = 1 and dn.status not in ('Closed', 'Stopped')
			and ifnull(dn_item.against_sales_order, '') = ''
			and ifnull(dn_item.against_sales_invoice, '') = ''""", (customer, company), as_dict=True)

	outstanding_based_on_dn = 0.0

	for dn_item in unmarked_delivery_note_items:
		si_amount = frappe.db.sql("""select sum(amount)
			from `tabSales Invoice Item`
			where dn_detail = %s and docstatus = 1""", dn_item.name)[0][0]

		if flt(dn_item.amount) > flt(si_amount) and dn_item.base_net_total:
			outstanding_based_on_dn += ((flt(dn_item.amount) - flt(si_amount)) \
				/ dn_item.base_net_total) * dn_item.base_grand_total

	return outstanding_based_on_gle + outstanding_based_on_so + outstanding_based_on_dn


def get_credit_limit(customer, company):
	credit_limit = None

	if customer:
		credit_limit, customer_group = frappe.db.get_value("Customer", customer, ["credit_limit", "customer_group"])

		if not credit_limit:
			credit_limit = frappe.db.get_value("Customer Group", customer_group, "credit_limit")

	if not credit_limit:
		credit_limit = frappe.db.get_value("Company", company, "credit_limit")

	return flt(credit_limit)
