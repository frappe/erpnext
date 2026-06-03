# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
import frappe.defaults
from frappe import _, msgprint, qb
from frappe.contacts.address_and_contact import (
	delete_contact_and_address,
	load_address_and_contact,
)
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series, set_name_from_naming_options
from frappe.model.utils.rename_doc import update_linked_doctypes
from frappe.query_builder import CustomFunction, Field, functions
from frappe.query_builder.functions import Cast, Coalesce, Max, Substring
from frappe.utils import cint, cstr, flt, get_formatted_email, today
from frappe.utils.user import get_users_with_role

from erpnext.accounts.party import (
	get_dashboard_info,
	validate_party_accounts,
	validate_party_currency_before_merging,
)
from erpnext.controllers.website_list_for_contact import add_role_for_portal_user
from erpnext.utilities.transaction_base import TransactionBase

from .mapper import (
	make_address,
	make_contact,
)


class Customer(TransactionBase):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.allowed_to_transact_with.allowed_to_transact_with import (
			AllowedToTransactWith,
		)
		from erpnext.accounts.doctype.party_account.party_account import PartyAccount
		from erpnext.selling.doctype.customer_credit_limit.customer_credit_limit import CustomerCreditLimit
		from erpnext.selling.doctype.sales_team.sales_team import SalesTeam
		from erpnext.selling.doctype.supplier_number_at_customer.supplier_number_at_customer import (
			SupplierNumberAtCustomer,
		)
		from erpnext.utilities.doctype.portal_user.portal_user import PortalUser

		account_manager: DF.Link | None
		accounts: DF.Table[PartyAccount]
		companies: DF.Table[AllowedToTransactWith]
		credit_limits: DF.Table[CustomerCreditLimit]
		customer_details: DF.Text | None
		customer_group: DF.Link | None
		customer_name: DF.Data
		customer_pos_id: DF.Data | None
		customer_primary_address: DF.Link | None
		customer_primary_contact: DF.Link | None
		customer_type: DF.Literal["Company", "Individual", "Partnership"]
		default_bank_account: DF.Link | None
		default_commission_rate: DF.Float
		default_currency: DF.Link | None
		default_price_list: DF.Link | None
		default_sales_partner: DF.Link | None
		disabled: DF.Check
		dn_required: DF.Check
		email_id: DF.ReadOnly | None
		first_name: DF.ReadOnly | None
		gender: DF.Link | None
		image: DF.AttachImage | None
		industry: DF.Link | None
		is_frozen: DF.Check
		is_internal_customer: DF.Check
		language: DF.Link | None
		last_name: DF.ReadOnly | None
		lead_name: DF.Link | None
		loyalty_program: DF.Link | None
		loyalty_program_tier: DF.Data | None
		market_segment: DF.Link | None
		mobile_no: DF.ReadOnly | None
		naming_series: DF.Literal["CUST-.YYYY.-"]
		opportunity_name: DF.Link | None
		payment_terms: DF.Link | None
		portal_users: DF.Table[PortalUser]
		primary_address: DF.TextEditor | None
		prospect_name: DF.Link | None
		represents_company: DF.Link | None
		sales_team: DF.Table[SalesTeam]
		so_required: DF.Check
		supplier_numbers: DF.Table[SupplierNumberAtCustomer]
		tax_category: DF.Link | None
		tax_id: DF.Data | None
		tax_withholding_category: DF.Link | None
		tax_withholding_group: DF.Link | None
		territory: DF.Link | None
		website: DF.Data | None
	# end: auto-generated types

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)
		self.load_dashboard_info()

	def load_dashboard_info(self):
		info = get_dashboard_info(self.doctype, self.name, self.loyalty_program)
		self.set_onload("dashboard_info", info)

	def autoname(self):
		cust_master_name = frappe.defaults.get_global_default("cust_master_name")
		if cust_master_name == "Customer Name":
			self.name = self.get_customer_name()
		elif cust_master_name == "Naming Series":
			set_name_by_naming_series(self)
		else:
			set_name_from_naming_options(frappe.get_meta(self.doctype).autoname, self)

	def get_customer_name(self):
		self.customer_name = self.customer_name.strip()
		if frappe.db.get_value("Customer", self.customer_name) and not frappe.flags.in_import:
			name_prefix = f"{self.customer_name} - %"
			Customer = frappe.qb.DocType("Customer")

			if frappe.db.db_type == "postgres":
				# Postgres: extract trailing digits (e.g. "Customer - 3") and cast to int.
				# NOTE: PostgreSQL is strict about types; MySQL's UNSIGNED cast does not exist.
				extracted_part = Substring(Customer.name, r"\d+$")
				casted_part = Cast(extracted_part, "INTEGER")
			else:
				# MariaDB/MySQL: keep existing behavior.
				SubstringIndex = CustomFunction("SUBSTRING_INDEX", ["str", "delim", "count"])
				extracted_part = SubstringIndex(Customer.name, " ", -1)
				casted_part = Cast(extracted_part, "UNSIGNED")

			query = (
				frappe.qb.from_(Customer)
				.select(Coalesce(Max(casted_part), 0))
				.where(Customer.name.like(name_prefix))
			)
			count = query.run()[0][0]
			count = cint(count) + 1

			new_customer_name = f"{self.customer_name} - {cstr(count)}"

			msgprint(
				_("Changed customer name to '{}' as '{}' already exists.").format(
					new_customer_name, self.customer_name
				),
				title=_("Note"),
				indicator="yellow",
				alert=True,
			)

			return new_customer_name

		return self.customer_name

	def after_insert(self):
		"""If customer created from Lead, update customer id in quotations, opportunities"""
		self.update_lead_status()

	def validate(self):
		self.flags.is_new_doc = self.is_new()
		self.flags.old_lead = self.lead_name
		self.validate_customer_group()
		validate_party_accounts(self)
		self.validate_credit_limit_on_change()
		self.set_loyalty_program()
		self.check_customer_group_change()
		self.validate_default_bank_account()
		self.validate_internal_customer()
		self.add_role_for_user()
		self.validate_currency_for_receivable_payable_and_advance_account()

		# set loyalty program tier
		if not self.is_new() and (customer := self.get_doc_before_save()):
			if self.loyalty_program == customer.loyalty_program and not self.loyalty_program_tier:
				self.loyalty_program_tier = customer.loyalty_program_tier

		if self.sales_team:
			if sum(member.allocated_percentage or 0 for member in self.sales_team) != 100:
				frappe.throw(_("Total contribution percentage should be equal to 100"))

	@frappe.whitelist()
	def get_customer_group_details(self):
		doc = frappe.get_doc("Customer Group", self.customer_group)
		self.accounts = []
		self.credit_limits = []
		self.payment_terms = self.default_price_list = ""

		tables = [["accounts", "account"], ["credit_limits", "credit_limit"]]
		fields = ["payment_terms", "default_price_list"]

		for row in tables:
			table, field = row[0], row[1]
			if not doc.get(table):
				continue

			for entry in doc.get(table):
				child = self.append(table)
				child.update({"company": entry.company, field: entry.get(field)})

		for field in fields:
			if not doc.get(field):
				continue
			self.update({field: doc.get(field)})

		self.save()

	def check_customer_group_change(self):
		frappe.flags.customer_group_changed = False

		if not self.get("__islocal"):
			if self.customer_group != frappe.db.get_value("Customer", self.name, "customer_group"):
				frappe.flags.customer_group_changed = True

	def validate_default_bank_account(self):
		if self.default_bank_account:
			is_company_account = frappe.db.get_value(
				"Bank Account", self.default_bank_account, "is_company_account"
			)
			if not is_company_account:
				frappe.throw(
					_("{0} is not a company bank account").format(frappe.bold(self.default_bank_account))
				)

	def validate_internal_customer(self):
		if not self.is_internal_customer:
			self.represents_company = ""
			return

		internal_customer = frappe.db.get_value(
			"Customer",
			{
				"is_internal_customer": 1,
				"represents_company": self.represents_company,
				"name": ("!=", self.name),
			},
			"name",
		)

		if internal_customer:
			frappe.throw(
				_("Internal Customer for company {0} already exists").format(
					frappe.bold(self.represents_company)
				)
			)

	def on_update(self):
		self.validate_name_with_customer_group()
		self.create_primary_contact()
		self.create_primary_address()

		if self.flags.old_lead != self.lead_name:
			self.update_lead_status()

		if self.flags.is_new_doc:
			self.link_address_and_contact()
			self.copy_communication()

		self.update_customer_groups()

	def add_role_for_user(self):
		for portal_user in self.portal_users:
			add_role_for_portal_user(portal_user, "Customer")

	def update_customer_groups(self):
		ignore_doctypes = ["Lead", "Opportunity", "POS Profile", "Tax Rule", "Pricing Rule"]
		if frappe.flags.customer_group_changed:
			update_linked_doctypes(
				"Customer", self.name, "Customer Group", self.customer_group, ignore_doctypes
			)

	def create_primary_contact(self):
		if not self.customer_primary_contact and not self.lead_name:
			if self.mobile_no or self.email_id or self.first_name or self.last_name:
				contact = make_contact(self)
				self.db_set("customer_primary_contact", contact.name)
				self.db_set("mobile_no", self.mobile_no)
				self.db_set("email_id", self.email_id)
		elif self.customer_primary_contact:
			frappe.set_value("Contact", self.customer_primary_contact, "is_primary_contact", 1)  # ensure

	def create_primary_address(self):
		from frappe.contacts.doctype.address.address import get_address_display

		if self.flags.is_new_doc and self.get("address_line1"):
			address = make_address(self)
			address_display = get_address_display(address.name)

			self.db_set("customer_primary_address", address.name)
			self.db_set("primary_address", address_display)
		elif self.customer_primary_address:
			frappe.set_value("Address", self.customer_primary_address, "is_primary_address", 1)  # ensure

	def update_lead_status(self):
		"""If Customer created from Lead, update lead status to "Converted"
		update Customer link in Quotation, Opportunity"""
		if self.lead_name:
			frappe.db.set_value("Lead", self.lead_name, "status", "Converted")

	def link_address_and_contact(self):
		linked_documents = {
			"Lead": self.lead_name,
			"Opportunity": self.opportunity_name,
			"Prospect": self.prospect_name,
		}
		for doctype, docname in linked_documents.items():
			# assign lead, opportunity and prospect address and contact to customer (if already not set)
			if not docname:
				continue

			linked_contacts_and_addresses = frappe.get_all(
				"Dynamic Link",
				filters=[
					["parenttype", "in", ["Contact", "Address"]],
					["link_doctype", "=", doctype],
					["link_name", "=", docname],
				],
				fields=["parent as name", "parenttype as doctype"],
			)

			for row in linked_contacts_and_addresses:
				linked_doc = frappe.get_doc(row.doctype, row.name)
				if not linked_doc.has_link("Customer", self.name):
					linked_doc.append("links", dict(link_doctype="Customer", link_name=self.name))
					linked_doc.save(ignore_permissions=self.flags.ignore_permissions)

	def copy_communication(self):
		if not self.lead_name or not frappe.db.get_single_value(
			"CRM Settings", "carry_forward_communication_and_comments"
		):
			return

		from erpnext.crm.utils import copy_comments, link_communications

		copy_comments("Lead", self.lead_name, self)
		link_communications("Lead", self.lead_name, self)

	def validate_name_with_customer_group(self):
		if frappe.db.exists("Customer Group", self.name):
			frappe.throw(
				_(
					"A Customer Group exists with same name please change the Customer name or rename the Customer Group"
				),
				frappe.NameError,
			)

	def validate_customer_group(self):
		if not self.customer_group:
			return

		is_group = frappe.db.get_value("Customer Group", self.customer_group, "is_group")
		if is_group:
			frappe.throw(
				_("Cannot select a Group type Customer Group. Please select a non-group Customer Group."),
				title=_("Invalid Customer Group"),
			)

	def validate_credit_limit_on_change(self):
		if self.get("__islocal") or not self.credit_limits:
			return

		past_credit_limits = [
			d.credit_limit
			for d in frappe.db.get_all(
				"Customer Credit Limit",
				filters={"parent": self.name},
				fields=["credit_limit"],
				order_by="company",
			)
		]

		current_credit_limits = [d.credit_limit for d in sorted(self.credit_limits, key=lambda k: k.company)]

		if past_credit_limits == current_credit_limits:
			return

		company_record = []
		for limit in self.credit_limits:
			if limit.company in company_record:
				frappe.throw(
					_("Credit limit is already defined for the Company {0}").format(limit.company, self.name)
				)
			else:
				company_record.append(limit.company)

			outstanding_amt = get_customer_outstanding(
				self.name, limit.company, ignore_outstanding_sales_order=limit.bypass_credit_limit_check
			)
			if flt(limit.credit_limit) < outstanding_amt:
				frappe.throw(
					_(
						"""New credit limit is less than current outstanding amount for the customer. Credit limit has to be atleast {0}"""
					).format(outstanding_amt)
				)

	def on_trash(self):
		if self.customer_primary_contact:
			self.db_set("customer_primary_contact", None)
		if self.customer_primary_address:
			self.db_set("customer_primary_address", None)

		delete_contact_and_address("Customer", self.name)
		if self.lead_name:
			frappe.db.set_value("Lead", self.lead_name, "status", "Interested")

	def before_rename(self, olddn, newdn, merge=False):
		if merge:
			validate_party_currency_before_merging("Customer", olddn, newdn)

	def after_rename(self, olddn, newdn, merge=False):
		if frappe.defaults.get_global_default("cust_master_name") == "Customer Name":
			self.db_set("customer_name", newdn)

	def set_loyalty_program(self):
		if self.loyalty_program:
			return

		loyalty_program = get_loyalty_programs(self)
		if not loyalty_program:
			return

		if len(loyalty_program) == 1:
			self.loyalty_program = loyalty_program[0]
		else:
			frappe.msgprint(
				_("Multiple Loyalty Programs found for Customer {}. Please select manually.").format(
					frappe.bold(self.customer_name)
				)
			)

	def get_notification_email(self):
		"""Hook to return the target email address for notifications."""
		if self.account_manager:
			return frappe.db.get_value("User", self.account_manager, "email")

		return None


@frappe.whitelist()
def get_loyalty_programs(doc: Document):
	"""returns applicable loyalty programs for a customer"""

	lp_details = []
	loyalty_programs = frappe.get_all(
		"Loyalty Program",
		fields=["name", "customer_group", "customer_territory"],
		filters=[
			["auto_opt_in", "=", 1],
			["from_date", "<=", today()],
			[functions.IfNull(Field("to_date"), "2500-01-01"), ">=", today()],
		],
	)

	for loyalty_program in loyalty_programs:
		if (
			not loyalty_program.customer_group
			or doc.customer_group
			in get_nested_links(
				"Customer Group", loyalty_program.customer_group, doc.flags.ignore_permissions
			)
		) and (
			not loyalty_program.customer_territory
			or doc.territory
			in get_nested_links("Territory", loyalty_program.customer_territory, doc.flags.ignore_permissions)
		):
			lp_details.append(loyalty_program.name)

	return lp_details


def get_nested_links(link_doctype, link_name, ignore_permissions=False):
	from frappe.desk.treeview import _get_children

	links = [link_name]
	for d in _get_children(link_doctype, link_name, ignore_permissions):
		links.append(d.value)

	return links


def check_credit_limit(customer, company, ignore_outstanding_sales_order=False, extra_amount=0):
	credit_limit = get_credit_limit(customer, company)
	if not credit_limit:
		return

	customer_outstanding = get_customer_outstanding(customer, company, ignore_outstanding_sales_order)
	if extra_amount > 0:
		customer_outstanding += flt(extra_amount)

	if credit_limit > 0 and flt(customer_outstanding) > credit_limit:
		message = _("Credit limit has been crossed for customer {0} ({1}/{2})").format(
			customer, customer_outstanding, credit_limit
		)

		message += "<br><br>"

		# If not authorized person raise exception
		credit_controller_role = frappe.get_single_value("Accounts Settings", "credit_controller")
		if not credit_controller_role or credit_controller_role not in frappe.get_roles():
			# form a list of emails for the credit controller users
			credit_controller_users = get_users_with_role(credit_controller_role or "Sales Master Manager")

			# form a list of emails and names to show to the user
			credit_controller_users_formatted = [
				get_formatted_email(user).replace("<", "(").replace(">", ")")
				for user in credit_controller_users
			]
			if not credit_controller_users_formatted:
				frappe.throw(
					_("Please contact your administrator to extend the credit limits for {0}.").format(
						customer
					)
				)

			user_list = "<br><br><ul><li>{}</li></ul>".format("<li>".join(credit_controller_users_formatted))

			message += _(
				"Please contact any of the following users to extend the credit limits for {0}: {1}"
			).format(customer, user_list)

			# if the current user does not have permissions to override credit limit,
			# prompt them to send out an email to the controller users
			frappe.msgprint(
				message,
				title=_("Credit Limit Crossed"),
				raise_exception=1,
				primary_action={
					"label": "Send Email",
					"server_action": "erpnext.selling.doctype.customer.customer.send_emails",
					"hide_on_success": True,
					"args": {
						"customer": customer,
						"customer_outstanding": customer_outstanding,
						"credit_limit": credit_limit,
						"credit_controller_users_list": credit_controller_users,
					},
				},
			)


@frappe.whitelist()
def send_emails(
	customer: str, customer_outstanding: float, credit_limit: float, credit_controller_users_list: str | list
):
	if isinstance(credit_controller_users_list, str):
		credit_controller_users_list = json.loads(credit_controller_users_list)
	subject = _("Credit limit reached for customer {0}").format(customer)
	message = _("Credit limit has been crossed for customer {0} ({1}/{2})").format(
		customer, customer_outstanding, credit_limit
	)
	frappe.sendmail(recipients=credit_controller_users_list, subject=subject, message=message)


def get_customer_outstanding(customer, company, ignore_outstanding_sales_order=False, cost_center=None):
	from frappe.query_builder import Criterion
	from frappe.query_builder.functions import Coalesce, IfNull, Sum

	GLEntry = frappe.qb.DocType("GL Entry")
	gle_query = (
		frappe.qb.from_(GLEntry)
		.select(Sum(GLEntry.debit) - Sum(GLEntry.credit))
		.where(GLEntry.party_type == "Customer")
		.where(GLEntry.party == customer)
		.where(GLEntry.company == company)
		.where(GLEntry.is_cancelled == 0)
	)

	if cost_center:
		lft, rgt = frappe.get_cached_value("Cost Center", cost_center, ["lft", "rgt"])
		CostCenter = frappe.qb.DocType("Cost Center")
		cost_center_subquery = (
			frappe.qb.from_(CostCenter)
			.select(CostCenter.name)
			.where(CostCenter.lft >= lft)
			.where(CostCenter.rgt <= rgt)
		)
		gle_query = gle_query.where(GLEntry.cost_center.isin(cost_center_subquery))

	gle_res = gle_query.run()
	outstanding_based_on_gle = flt(gle_res[0][0]) if gle_res and gle_res[0][0] is not None else 0.0

	outstanding_based_on_so = 0.0
	if not ignore_outstanding_sales_order:
		SalesOrder = frappe.qb.DocType("Sales Order")
		so_query = (
			frappe.qb.from_(SalesOrder)
			.select(Sum(SalesOrder.base_grand_total * (100 - SalesOrder.per_billed) / 100))
			.where(SalesOrder.customer == customer)
			.where(SalesOrder.company == company)
			.where(SalesOrder.docstatus == 1)
			.where(SalesOrder.per_billed < 100)
			.where(SalesOrder.status != "Closed")
		)
		so_res = so_query.run()
		outstanding_based_on_so = flt(so_res[0][0]) if so_res and so_res[0][0] is not None else 0.0

	DeliveryNote = frappe.qb.DocType("Delivery Note")
	DeliveryNoteItem = frappe.qb.DocType("Delivery Note Item")
	SalesInvoiceItem = frappe.qb.DocType("Sales Invoice Item")

	si_subquery = (
		frappe.qb.from_(SalesInvoiceItem)
		.select(SalesInvoiceItem.dn_detail, Sum(SalesInvoiceItem.amount).as_("billed_amount"))
		.where(SalesInvoiceItem.docstatus == 1)
		.groupby(SalesInvoiceItem.dn_detail)
	)

	dn_query = (
		frappe.qb.from_(DeliveryNote)
		.join(DeliveryNoteItem)
		.on(DeliveryNote.name == DeliveryNoteItem.parent)
		.left_join(si_subquery)
		.on(DeliveryNoteItem.name == si_subquery.dn_detail)
		.select(
			Sum(
				(
					(DeliveryNoteItem.amount - IfNull(si_subquery.billed_amount, 0.0))
					/ DeliveryNote.base_net_total
				)
				* DeliveryNote.base_grand_total
			)
		)
		.where(DeliveryNote.customer == customer)
		.where(DeliveryNote.company == company)
		.where(DeliveryNote.docstatus == 1)
		.where(DeliveryNote.base_net_total > 0)
		.where(DeliveryNote.status.notin(["Closed", "Stopped"]))
		.where(DeliveryNoteItem.amount > IfNull(si_subquery.billed_amount, 0.0))
		.where(
			Criterion.any(
				[DeliveryNoteItem.against_sales_order.isnull(), DeliveryNoteItem.against_sales_order == ""]
			)
		)
		.where(
			Criterion.any(
				[
					DeliveryNoteItem.against_sales_invoice.isnull(),
					DeliveryNoteItem.against_sales_invoice == "",
				]
			)
		)
	)

	dn_res = dn_query.run()
	outstanding_based_on_dn = flt(dn_res[0][0]) if dn_res and dn_res[0][0] is not None else 0.0

	return outstanding_based_on_gle + outstanding_based_on_so + outstanding_based_on_dn


def get_credit_limit(customer, company):
	credit_limit = None

	if customer:
		credit_limit = frappe.db.get_value(
			"Customer Credit Limit",
			{"parent": customer, "parenttype": "Customer", "company": company},
			"credit_limit",
		)

		if not credit_limit:
			customer_group = frappe.get_cached_value("Customer", customer, "customer_group")

			result = frappe.db.get_values(
				"Customer Credit Limit",
				{"parent": customer_group, "parenttype": "Customer Group", "company": company},
				fieldname=["credit_limit", "bypass_credit_limit_check"],
				as_dict=True,
			)
			if result and not result[0].bypass_credit_limit_check:
				credit_limit = result[0].credit_limit

	if not credit_limit:
		credit_limit = frappe.get_cached_value("Company", company, "credit_limit")

	return flt(credit_limit)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_customer_primary(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	customer = filters.get("customer")
	type = filters.get("type")
	type_doctype = qb.DocType(type)
	dlink = qb.DocType("Dynamic Link")

	query = (
		qb.from_(type_doctype)
		.join(dlink)
		.on(type_doctype.name == dlink.parent)
		.select(type_doctype.name)
		.where(
			(dlink.link_name == customer)
			& (type_doctype.name.like(f"%{txt}%"))
			& (dlink.link_doctype == "Customer")
		)
	)

	if type == "Contact":
		query = query.select(type_doctype.email_id)

	return query.run()
