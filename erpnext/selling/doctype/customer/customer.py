# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.naming import make_autoname
from frappe import _, msgprint, throw
import frappe.defaults
from frappe.utils import flt


from erpnext.utilities.transaction_base import TransactionBase

class Customer(TransactionBase):
	def get_feed(self):
		return self.customer_name

	def autoname(self):
		cust_master_name = frappe.defaults.get_global_default('cust_master_name')
		if cust_master_name == 'Customer Name':
			self.name = self.customer_name
		else:
			self.name = make_autoname(self.naming_series+'.#####')

	def get_company_abbr(self):
		return frappe.db.get_value('Company', self.company, 'abbr')

	def validate_values(self):
		if frappe.defaults.get_global_default('cust_master_name') == 'Naming Series' and not self.naming_series:
			frappe.throw(_("Series is mandatory"), frappe.MandatoryError)

	def validate(self):
		self.validate_values()

	def update_lead_status(self):
		if self.lead_name:
			frappe.db.sql("update `tabLead` set status='Converted' where name = %s", self.lead_name)

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
			c.ignore_permissions = getattr(self, "ignore_permissions", None)
			c.autoname()
			if not frappe.db.exists("Contact", c.name):
				c.insert()

	def on_update(self):
		self.validate_name_with_customer_group()

		self.update_lead_status()
		self.update_address()
		self.update_contact()
		self.create_lead_address_contact()

	def validate_name_with_customer_group(self):
		if frappe.db.exists("Customer Group", self.name):
			frappe.throw(_("A Customer Group exists with same name please change the Customer name or rename the Customer Group"))

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

@frappe.whitelist()
def get_dashboard_info(customer):
	if not frappe.has_permission("Customer", "read", customer):
		frappe.msgprint(_("Not permitted"), raise_exception=True)

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


def check_credit_limit(customer, company):
	customer_outstanding = get_customer_outstanding(customer, company)

	credit_limit = frappe.db.get_value("Customer", customer, "credit_limit") or \
		frappe.db.get_value('Company', company, 'credit_limit')

	if credit_limit > 0 and flt(customer_outstanding) > credit_limit:
		msgprint(_("Credit limit has been crossed for customer {0} {1}/{2}")
			.format(customer, customer_outstanding, credit_limit))

		# If not authorized person raise exception
		credit_controller = frappe.db.get_value('Accounts Settings', None, 'credit_controller')
		if not credit_controller or credit_controller not in frappe.user.get_roles():
			throw(_("Please contact to the user who have Sales Master Manager {0} role")
				.format(" / " + credit_controller if credit_controller else ""))

def get_customer_outstanding(customer, company):
	# Outstanding based on GL Entries
	outstanding_based_on_gle = frappe.db.sql("""select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
		from `tabGL Entry` where party_type = 'Customer' and party = %s and company=%s""", (customer, company))

	outstanding_based_on_gle = flt(outstanding_based_on_gle[0][0]) if outstanding_based_on_gle else 0

	# Outstanding based on Sales Order
	outstanding_based_on_so = frappe.db.sql("""
		select sum(grand_total*(100 - ifnull(per_billed, 0))/100)
		from `tabSales Order`
		where customer=%s and docstatus = 1 and company=%s
		and ifnull(per_billed, 0) < 100 and status != 'Stopped'""", (customer, company))

	outstanding_based_on_so = flt(outstanding_based_on_so[0][0]) if outstanding_based_on_so else 0.0

	# Outstanding based on Delivery Note
	outstanding_based_on_dn = frappe.db.sql("""
		select
			sum(
				(
					(ifnull(dn_item.amount) - (select sum(ifnull(amount, 0))
						from `tabSales Invoice Item`
						where ifnull(dn_detail, '') = dn_item.name and docstatus = 1)
					)/dn.net_total
				)*dn.grand_total
			)
		from `tabDelivery Note` dn, `tabDelivery Note Item` dn_item
		where
			dn.name = dn_item.parent and dn.customer=%s and dn.company=%s
			and dn.docstatus = 1 and dn.status != 'Stopped'
			and ifnull(dn_item.against_sales_order, '') = ''
			and ifnull(dn_item.against_sales_invoice, '') = ''
			and ifnull(dn_item.amount) > (select sum(ifnull(amount, 0))
				from `tabSales Invoice Item`
				where ifnull(dn_detail, '') = dn_item.name and docstatus = 1)""", (customer, company))

	outstanding_based_on_dn = flt(outstanding_based_on_dn[0][0]) if outstanding_based_on_dn else 0.0

	return outstanding_based_on_gle + outstanding_based_on_so + outstanding_based_on_dn
