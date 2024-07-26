# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
import frappe.defaults
from frappe import _, msgprint
from frappe.contacts.address_and_contact import (
	delete_contact_and_address,
	load_address_and_contact,
)
from frappe.model.naming import set_name_by_naming_series, set_name_from_naming_options

from erpnext.accounts.party import (
	get_dashboard_info,
	validate_party_accounts,
)
from erpnext.controllers.website_list_for_contact import add_role_for_portal_user
from erpnext.utilities.transaction_base import TransactionBase


class Supplier(TransactionBase):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.allowed_to_transact_with.allowed_to_transact_with import (
			AllowedToTransactWith,
		)
		from erpnext.accounts.doctype.party_account.party_account import PartyAccount
		from erpnext.utilities.doctype.portal_user.portal_user import PortalUser

		accounts: DF.Table[PartyAccount]
		allow_purchase_invoice_creation_without_purchase_order: DF.Check
		allow_purchase_invoice_creation_without_purchase_receipt: DF.Check
		companies: DF.Table[AllowedToTransactWith]
		country: DF.Link | None
		default_bank_account: DF.Link | None
		default_currency: DF.Link | None
		default_price_list: DF.Link | None
		disabled: DF.Check
		email_id: DF.ReadOnly | None
		hold_type: DF.Literal["", "All", "Invoices", "Payments"]
		image: DF.AttachImage | None
		is_frozen: DF.Check
		is_internal_supplier: DF.Check
		is_transporter: DF.Check
		language: DF.Link | None
		mobile_no: DF.ReadOnly | None
		naming_series: DF.Literal["SUP-.YYYY.-"]
		on_hold: DF.Check
		payment_terms: DF.Link | None
		portal_users: DF.Table[PortalUser]
		prevent_pos: DF.Check
		prevent_rfqs: DF.Check
		primary_address: DF.Text | None
		release_date: DF.Date | None
		represents_company: DF.Link | None
		supplier_details: DF.Text | None
		supplier_group: DF.Link | None
		supplier_name: DF.Data
		supplier_primary_address: DF.Link | None
		supplier_primary_contact: DF.Link | None
		supplier_type: DF.Literal["Company", "Individual", "Partnership"]
		tax_category: DF.Link | None
		tax_id: DF.Data | None
		tax_withholding_category: DF.Link | None
		warn_pos: DF.Check
		warn_rfqs: DF.Check
		website: DF.Data | None
	# end: auto-generated types

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)
		self.load_dashboard_info()

	def before_save(self):
		if not self.on_hold:
			self.hold_type = ""
			self.release_date = ""
		elif self.on_hold and not self.hold_type:
			self.hold_type = "All"

	def load_dashboard_info(self):
		info = get_dashboard_info(self.doctype, self.name)
		self.set_onload("dashboard_info", info)

	def autoname(self):
		supp_master_name = frappe.defaults.get_global_default("supp_master_name")
		if supp_master_name == "Supplier Name":
			self.name = self.supplier_name
		elif supp_master_name == "Naming Series":
			set_name_by_naming_series(self)
		else:
			self.name = set_name_from_naming_options(frappe.get_meta(self.doctype).autoname, self)

	def on_update(self):
		self.create_primary_contact()
		self.create_primary_address()

	def add_role_for_user(self):
		for portal_user in self.portal_users:
			add_role_for_portal_user(portal_user, "Supplier")

	def _add_supplier_role(self, portal_user):
		if not portal_user.is_new():
			return

		user_doc = frappe.get_doc("User", portal_user.user)
		roles = {r.role for r in user_doc.roles}

		if "Supplier" in roles:
			return

		if "System Manager" not in frappe.get_roles():
			frappe.msgprint(
				_("Please add 'Supplier' role to user {0}.").format(portal_user.user),
				alert=True,
			)
			return

		user_doc.add_roles("Supplier")
		frappe.msgprint(_("Added Supplier Role to User {0}.").format(frappe.bold(user_doc.name)), alert=True)

	def validate(self):
		self.flags.is_new_doc = self.is_new()

		# validation for Naming Series mandatory field...
		if frappe.defaults.get_global_default("supp_master_name") == "Naming Series":
			if not self.naming_series:
				msgprint(_("Series is mandatory"), raise_exception=1)

		validate_party_accounts(self)
		self.validate_internal_supplier()
		self.add_role_for_user()
		self.validate_currency_for_receivable_payable_and_advance_account()

	@frappe.whitelist()
	def get_supplier_group_details(self):
		doc = frappe.get_doc("Supplier Group", self.supplier_group)
		self.payment_terms = ""
		self.accounts = []

		if doc.accounts:
			for account in doc.accounts:
				child = self.append("accounts")
				child.company = account.company
				child.account = account.account

		if doc.payment_terms:
			self.payment_terms = doc.payment_terms

		self.save()

	def validate_internal_supplier(self):
		if not self.is_internal_supplier:
			self.represents_company = ""

		internal_supplier = frappe.db.get_value(
			"Supplier",
			{
				"is_internal_supplier": 1,
				"represents_company": self.represents_company,
				"name": ("!=", self.name),
			},
			"name",
		)

		if internal_supplier:
			frappe.throw(
				_("Internal Supplier for company {0} already exists").format(
					frappe.bold(self.represents_company)
				)
			)

	def create_primary_contact(self):
		from erpnext.selling.doctype.customer.customer import make_contact

		if not self.supplier_primary_contact:
			if self.mobile_no or self.email_id:
				contact = make_contact(self)
				self.db_set("supplier_primary_contact", contact.name)
				self.db_set("mobile_no", self.mobile_no)
				self.db_set("email_id", self.email_id)

	def create_primary_address(self):
		from frappe.contacts.doctype.address.address import get_address_display

		from erpnext.selling.doctype.customer.customer import make_address

		if self.flags.is_new_doc and self.get("address_line1"):
			address = make_address(self)
			address_display = get_address_display(address.name)

			self.db_set("supplier_primary_address", address.name)
			self.db_set("primary_address", address_display)

	def on_trash(self):
		if self.supplier_primary_contact:
			self.db_set("supplier_primary_contact", None)
		if self.supplier_primary_address:
			self.db_set("supplier_primary_address", None)

		delete_contact_and_address("Supplier", self.name)

	def after_rename(self, olddn, newdn, merge=False):
		if frappe.defaults.get_global_default("supp_master_name") == "Supplier Name":
			self.db_set("supplier_name", newdn)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_supplier_primary_contact(doctype, txt, searchfield, start, page_len, filters):
	supplier = filters.get("supplier")
	contact = frappe.qb.DocType("Contact")
	dynamic_link = frappe.qb.DocType("Dynamic Link")

	return (
		frappe.qb.from_(contact)
		.join(dynamic_link)
		.on(contact.name == dynamic_link.parent)
		.select(contact.name, contact.email_id)
		.where(
			(dynamic_link.link_name == supplier)
			& (dynamic_link.link_doctype == "Supplier")
			& (contact.name.like(f"%{txt}%"))
		)
	).run(as_dict=False)
