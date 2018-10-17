# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.naming import set_name_by_naming_series
from frappe import _, msgprint, throw
import frappe.defaults
from frappe.utils import flt, cint, cstr, today
from frappe.desk.reportview import build_match_conditions, get_filters_cond
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import validate_party_accounts, get_dashboard_info, get_timeline_data # keep this
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address
from frappe.model.rename_doc import update_linked_doctypes
from erpnext import get_default_company

class Customer(TransactionBase):
	def get_feed(self):
		return self.customer_name

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)
		self.load_dashboard_info()

	def load_dashboard_info(self):
		info = get_dashboard_info(self.doctype, self.name)
		loyalty_point_details = self.get_loyalty_points()
		if loyalty_point_details and loyalty_point_details.get("loyalty_points"):
			info["loyalty_point"] = loyalty_point_details.loyalty_points
		self.set_onload('dashboard_info', info)

	def autoname(self):
		cust_master_name = frappe.defaults.get_global_default('cust_master_name')
		if cust_master_name == 'Customer Name':
			self.name = self.get_customer_name()
		else:
			set_name_by_naming_series(self)

	def get_loyalty_points(self):
		if self.loyalty_program:
			from erpnext.accounts.doctype.loyalty_program.loyalty_program import get_loyalty_details
			return get_loyalty_details(self.name, self.loyalty_program)

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
		if frappe.db.get_single_value('Accounts Settings', 'create_customer_account_after_insert'):
			parent_account = frappe.db.get_single_value('Accounts Settings', 'customer_parent_account')
			self.create_customer_account(parent_account)

	def validate(self):
		self.flags.is_new_doc = self.is_new()
		self.flags.old_lead = self.lead_name
		validate_party_accounts(self)
		self.validate_credit_limit_on_change()
		self.set_loyalty_program()
		self.check_customer_group_change()

		# set loyalty program tier
		if frappe.db.exists('Customer', self.name):
			customer = frappe.get_doc('Customer', self.name)
			if self.loyalty_program == customer.loyalty_program and not self.loyalty_program_tier:
				self.loyalty_program_tier = customer.loyalty_program_tier

	def check_customer_group_change(self):
		frappe.flags.customer_group_changed = False

		if not self.get('__islocal'):
			if self.customer_group != frappe.db.get_value('Customer', self.name, 'customer_group'):
				frappe.flags.customer_group_changed = True

	def on_update(self):
		self.validate_name_with_customer_group()
		self.create_primary_contact()
		self.create_primary_address()

		if self.flags.old_lead != self.lead_name:
			self.update_lead_status()

		if self.flags.is_new_doc:
			self.create_lead_address_contact()

		self.update_customer_groups()

	def update_customer_groups(self):
		ignore_doctypes = ["Lead", "Opportunity", "POS Profile", "Tax Rule", "Pricing Rule"]
		if frappe.flags.customer_group_changed:
			update_linked_doctypes('Customer', frappe.db.escape(self.name), 'Customer Group',
				self.customer_group, ignore_doctypes)

	def create_primary_contact(self):
		if not self.customer_primary_contact and not self.lead_name:
			if self.mobile_no or self.email_id:
				contact = make_contact(self)
				self.db_set('customer_primary_contact', contact.name)
				self.db_set('mobile_no', self.mobile_no)
				self.db_set('email_id', self.email_id)

	def create_primary_address(self):
		if self.flags.is_new_doc and self.get('address_line1'):
			make_address(self)

	def update_lead_status(self):
		'''If Customer created from Lead, update lead status to "Converted"
		update Customer link in Quotation, Opportunity'''
		if self.lead_name:
			frappe.db.set_value('Lead', self.lead_name, 'status', 'Converted', update_modified=False)

			for doctype in ('Opportunity', 'Quotation'):
				for d in frappe.get_all(doctype, {'lead': self.lead_name}):
					frappe.db.set_value(doctype, d.name, 'customer', self.name, update_modified=False)

	def create_lead_address_contact(self):
		if self.lead_name:
			# assign lead address to customer (if already not set)
			address_names = frappe.get_all('Dynamic Link', filters={
								"parenttype":"Address",
								"link_doctype":"Lead",
								"link_name":self.lead_name
							}, fields=["parent as name"])

			for address_name in address_names:
				address = frappe.get_doc('Address', address_name.get('name'))
				if not address.has_link('Customer', self.name):
					address.append('links', dict(link_doctype='Customer', link_name=self.name))
					address.save()

			lead = frappe.db.get_value("Lead", self.lead_name, ["organization_lead", "lead_name", "email_id", "phone", "mobile_no", "gender", "salutation"], as_dict=True)

			if not lead.lead_name:
				frappe.throw(_("Please mention the Lead Name in Lead {0}").format(self.lead_name))

			if lead.organization_lead:
				contact_names = frappe.get_all('Dynamic Link', filters={
									"parenttype":"Contact",
									"link_doctype":"Lead",
									"link_name":self.lead_name
								}, fields=["parent as name"])

				for contact_name in contact_names:
					contact = frappe.get_doc('Contact', contact_name.get('name'))
					if not contact.has_link('Customer', self.name):
						contact.append('links', dict(link_doctype='Customer', link_name=self.name))
						contact.save()

			else:
				lead.lead_name = lead.lead_name.split(" ")
				lead.first_name = lead.lead_name[0]
				lead.last_name = " ".join(lead.lead_name[1:])

				# create contact from lead
				contact = frappe.new_doc('Contact')
				contact.first_name = lead.first_name
				contact.last_name = lead.last_name
				contact.gender = lead.gender
				contact.salutation = lead.salutation
				contact.email_id = lead.email_id
				contact.phone = lead.phone
				contact.mobile_no = lead.mobile_no
				contact.is_primary_contact = 1
				contact.append('links', dict(link_doctype='Customer', link_name=self.name))
				contact.flags.ignore_permissions = self.flags.ignore_permissions
				contact.autoname()
				if not frappe.db.exists("Contact", contact.name):
					contact.insert()

	def validate_name_with_customer_group(self):
		if frappe.db.exists("Customer Group", self.name):
			frappe.throw(_("A Customer Group exists with same name please change the Customer name or rename the Customer Group"), frappe.NameError)

	def validate_credit_limit_on_change(self):
		if self.get("__islocal") or not self.credit_limit \
			or self.credit_limit == frappe.db.get_value("Customer", self.name, "credit_limit"):
			return

		for company in frappe.get_all("Company"):
			outstanding_amt = get_customer_outstanding(self.name, company.name)
			if flt(self.credit_limit) < outstanding_amt:
				frappe.throw(_("""New credit limit is less than current outstanding amount for the customer. Credit limit has to be atleast {0}""").format(outstanding_amt))

	def on_trash(self):
		delete_contact_and_address('Customer', self.name)
		if self.lead_name:
			frappe.db.sql("update `tabLead` set status='Interested' where name=%s", self.lead_name)

	def after_rename(self, olddn, newdn, merge=False):
		if frappe.defaults.get_global_default('cust_master_name') == 'Customer Name':
			frappe.db.set(self, "customer_name", newdn)
      
	def set_loyalty_program(self):
		if self.loyalty_program: return
		loyalty_program = get_loyalty_programs(self)
		if not loyalty_program: return
		if len(loyalty_program) == 1:
			self.loyalty_program = loyalty_program[0]
		else:
			frappe.msgprint(_("Multiple Loyalty Program found for the Customer. Please select manually."))

@frappe.whitelist()
def get_loyalty_programs(doc):
	''' returns applicable loyalty programs for a customer '''
	from frappe.desk.treeview import get_children

	lp_details = []
	loyalty_programs = frappe.get_all("Loyalty Program",
		fields=["name", "customer_group", "customer_territory"],
		filters={"auto_opt_in": 1, "from_date": ["<=", today()],
			"ifnull(to_date, '2500-01-01')": [">=", today()]})

	for loyalty_program in loyalty_programs:
		customer_groups = [d.value for d in get_children("Customer Group", loyalty_program.customer_group)] + [loyalty_program.customer_group]
		customer_territories = [d.value for d in get_children("Territory", loyalty_program.customer_territory)] + [loyalty_program.customer_territory]

		if (not loyalty_program.customer_group or doc.customer_group in customer_groups)\
			and (not loyalty_program.customer_territory or doc.territory in customer_territories):
			lp_details.append(loyalty_program.name)

	return lp_details

	def create_customer_account(self,parent_account):
		account = frappe.get_doc({
			"doctype": "Account",
			"account_name": self.customer_name,
			"parent_account":parent_account,
			"company": get_default_company(),
			"is_group": 0,
			"account_type": "Receivable",
		}).insert()

		account_party = frappe.get_doc({
			"doctype": "Party Account",
			"company": get_default_company(),
			"account":  account.name
		})
		self.append("accounts", account_party)
		self.save()

def get_customer_list(doctype, txt, searchfield, start, page_len, filters=None):
	if frappe.db.get_default("cust_master_name") == "Customer Name":
		fields = ["name", "customer_group", "territory"]
	else:
		fields = ["name", "customer_name", "customer_group", "territory"]

	match_conditions = build_match_conditions("Customer")
	match_conditions = "and {}".format(match_conditions) if match_conditions else ""

	if filters:
		filter_conditions = get_filters_cond(doctype, filters, [])
		match_conditions += "{}".format(filter_conditions)

	return frappe.db.sql("""select %s from `tabCustomer` where docstatus < 2
		and (%s like %s or customer_name like %s)
		{match_conditions}
		order by
		case when name like %s then 0 else 1 end,
		case when customer_name like %s then 0 else 1 end,
		name, customer_name limit %s, %s""".format(match_conditions=match_conditions) %
		(", ".join(fields), searchfield, "%s", "%s", "%s", "%s", "%s", "%s"),
		("%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, start, page_len))


def check_credit_limit(customer, company, ignore_outstanding_sales_order=False, extra_amount=0):
	customer_outstanding = get_customer_outstanding(customer, company, ignore_outstanding_sales_order)
	if extra_amount > 0:
		customer_outstanding += flt(extra_amount)

	credit_limit = get_credit_limit(customer, company)
	if credit_limit > 0 and flt(customer_outstanding) > credit_limit:
		msgprint(_("Credit limit has been crossed for customer {0} ({1}/{2})")
			.format(customer, customer_outstanding, credit_limit))

		# If not authorized person raise exception
		credit_controller = frappe.db.get_value('Accounts Settings', None, 'credit_controller')
		if not credit_controller or credit_controller not in frappe.get_roles():
			throw(_("Please contact to the user who have Sales Master Manager {0} role")
				.format(" / " + credit_controller if credit_controller else ""))

def get_customer_outstanding(customer, company, ignore_outstanding_sales_order=False):
	# Outstanding based on GL Entries
	outstanding_based_on_gle = frappe.db.sql("""
		select sum(debit) - sum(credit)
		from `tabGL Entry`
		where party_type = 'Customer' and party = %s and company=%s""", (customer, company))

	outstanding_based_on_gle = flt(outstanding_based_on_gle[0][0]) if outstanding_based_on_gle else 0

	# Outstanding based on Sales Order
	outstanding_based_on_so = 0.0

	# if credit limit check is bypassed at sales order level,
	# we should not consider outstanding Sales Orders, when customer credit balance report is run
	if not ignore_outstanding_sales_order:
		outstanding_based_on_so = frappe.db.sql("""
			select sum(base_grand_total*(100 - per_billed)/100)
			from `tabSales Order`
			where customer=%s and docstatus = 1 and company=%s
			and per_billed < 100 and status != 'Closed'""", (customer, company))

		outstanding_based_on_so = flt(outstanding_based_on_so[0][0]) if outstanding_based_on_so else 0.0

	# Outstanding based on Delivery Note, which are not created against Sales Order
	unmarked_delivery_note_items = frappe.db.sql("""select
			dn_item.name, dn_item.amount, dn.base_net_total, dn.base_grand_total
		from `tabDelivery Note` dn, `tabDelivery Note Item` dn_item
		where
			dn.name = dn_item.parent
			and dn.customer=%s and dn.company=%s
			and dn.docstatus = 1 and dn.status not in ('Closed', 'Stopped')
			and ifnull(dn_item.against_sales_order, '') = ''
			and ifnull(dn_item.against_sales_invoice, '') = ''
		""", (customer, company), as_dict=True)

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
		credit_limit, customer_group = frappe.get_cached_value("Customer",
			customer, ["credit_limit", "customer_group"])

		if not credit_limit:
			credit_limit = frappe.get_cached_value("Customer Group", customer_group, "credit_limit")

	if not credit_limit:
		credit_limit = frappe.get_cached_value('Company',  company,  "credit_limit")

	return flt(credit_limit)

def make_contact(args, is_primary_contact=1):
	contact = frappe.get_doc({
		'doctype': 'Contact',
		'first_name': args.get('name'),
		'mobile_no': args.get('mobile_no'),
		'email_id': args.get('email_id'),
		'is_primary_contact': is_primary_contact,
		'links': [{
			'link_doctype': args.get('doctype'),
			'link_name': args.get('name')
		}]
	}).insert()

	return contact

def make_address(args, is_primary_address=1):
	address = frappe.get_doc({
		'doctype': 'Address',
		'address_title': args.get('name'),
		'address_line1': args.get('address_line1'),
		'address_line2': args.get('address_line2'),
		'city': args.get('city'),
		'state': args.get('state'),
		'pincode': args.get('pincode'),
		'country': args.get('country'),
		'links': [{
			'link_doctype': args.get('doctype'),
			'link_name': args.get('name')
		}]
	}).insert()

	return address

def get_customer_primary_contact(doctype, txt, searchfield, start, page_len, filters):
	customer = filters.get('customer')
	return frappe.db.sql("""
		select `tabContact`.name from `tabContact`, `tabDynamic Link`
			where `tabContact`.name = `tabDynamic Link`.parent and `tabDynamic Link`.link_name = %(customer)s
			and `tabDynamic Link`.link_doctype = 'Customer' and `tabContact`.is_primary_contact = 1
			and `tabContact`.name like %(txt)s
		""", {
			'customer': customer,
			'txt': '%%%s%%' % txt
		})

def get_customer_primary_address(doctype, txt, searchfield, start, page_len, filters):
	customer = frappe.db.escape(filters.get('customer'))
	return frappe.db.sql("""
		select `tabAddress`.name from `tabAddress`, `tabDynamic Link`
			where `tabAddress`.name = `tabDynamic Link`.parent and `tabDynamic Link`.link_name = %(customer)s
			and `tabDynamic Link`.link_doctype = 'Customer' and `tabAddress`.is_primary_address = 1
			and `tabAddress`.name like %(txt)s
		""", {
			'customer': customer,
			'txt': '%%%s%%' % txt
		})
