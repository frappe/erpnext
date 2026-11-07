# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, formatdate, getdate


class BankGuarantee(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		amended_from: DF.Link | None
		amount: DF.Currency
		bank: DF.Link | None
		bank_account: DF.Link | None
		bank_account_no: DF.Data | None
		bank_guarantee_number: DF.Data | None
		bg_type: DF.Literal["", "Receiving", "Providing"]
		branch_code: DF.Data | None
		charges: DF.Currency
		customer: DF.Link | None
		end_date: DF.Date | None
		fixed_deposit_number: DF.Data | None
		iban: DF.Data | None
		margin_money: DF.Currency
		more_information: DF.TextEditor | None
		name_of_beneficiary: DF.Data | None
		project: DF.Link | None
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		start_date: DF.Date
		supplier: DF.Link | None
		swift_number: DF.Data | None
		validity: DF.Int
	# end: auto-generated types

	def validate(self):
		self.validate_reference()
		if not (self.customer or self.supplier):
			frappe.throw(_("Select the customer or supplier."))
		self.set_end_date()

	def validate_reference(self):
		"""The reference is a submitted order of the guarantee's type; the party and project come from it."""
		reference_doctype, party_field, other_party_field = (
			("Sales Order", "customer", "supplier")
			if self.bg_type == "Receiving"
			else ("Purchase Order", "supplier", "customer")
		)
		if self.reference_docname and self.reference_doctype != reference_doctype:
			frappe.throw(
				_("The reference of a {0} Bank Guarantee must be a {1}.").format(
					_(self.bg_type), _(reference_doctype)
				),
				title=_("Invalid Reference"),
			)
		self.reference_doctype = reference_doctype
		self.set(other_party_field, None)

		if not self.reference_docname:
			return

		order = frappe.db.get_value(
			reference_doctype,
			self.reference_docname,
			["docstatus", party_field, "project"],
			as_dict=True,
		)
		if order:
			validate_reference_company(reference_doctype, self.reference_docname)
		if not order or order.docstatus != 1:
			frappe.throw(
				_("{0} {1} must be submitted.").format(
					_(reference_doctype), frappe.bold(self.reference_docname)
				),
				title=_("Invalid Reference"),
			)

		self.set(party_field, order.get(party_field))
		if order.project:
			self.project = order.project

	def set_end_date(self):
		if cint(self.validity) > 0:
			self.end_date = add_days(self.start_date, cint(self.validity) - 1)

		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(
				_("End Date {0} cannot be before Start Date {1}. Set the Validity in Days.").format(
					frappe.bold(formatdate(self.end_date)), frappe.bold(formatdate(self.start_date))
				),
				title=_("Invalid Dates"),
			)

	def on_submit(self):
		if not self.bank_guarantee_number:
			frappe.throw(_("Enter the Bank Guarantee Number before submitting."))
		if not self.name_of_beneficiary:
			frappe.throw(_("Enter the name of the Beneficiary before submitting."))
		if not self.bank:
			frappe.throw(_("Enter the name of the bank or lending institution before submitting."))


@frappe.whitelist()
def get_voucher_details(bank_guarantee_type: str, reference_name: str):
	if not isinstance(reference_name, str):
		raise TypeError("reference_name must be a string")

	# the form is the boundary, not the referenced order: an order guard would break one of the two roles
	frappe.has_permission("Bank Guarantee", throw=True)

	fields_to_fetch = ["grand_total"]

	if bank_guarantee_type == "Receiving":
		doctype = "Sales Order"
		fields_to_fetch.append("customer")
		fields_to_fetch.append("project")
	else:
		doctype = "Purchase Order"
		fields_to_fetch.append("supplier")

	# and scope the referenced order to the caller's own Company restrictions, which costs nobody
	# who has none
	validate_reference_company(doctype, reference_name)

	return frappe.db.get_value(doctype, reference_name, fields_to_fetch, as_dict=True)


def validate_reference_company(doctype, name):
	from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_companies

	allowed_companies = get_allowed_companies(frappe.session.user, "Bank Guarantee")
	if allowed_companies:
		company = frappe.db.get_value(doctype, name, "company")
		if company and company not in allowed_companies:
			frappe.throw(_("Not permitted for {0}").format(company), frappe.PermissionError)
