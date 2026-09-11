# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


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
		if not (self.customer or self.supplier):
			frappe.throw(_("Select the customer or supplier."))

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

	# This picker only exists on the Bank Guarantee form, so that form is what entitles a caller to
	# it. Deliberately NOT a check on the referenced order: Bank Guarantee is held by Accounts
	# Manager and Accounts User only, and Accounts Manager holds no Sales Order read while Accounts
	# User holds no Purchase Order read — an order-level guard would break one of the two roles on
	# whichever side they were using.
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
	from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_companies

	allowed_companies = get_allowed_companies(frappe.session.user, "Bank Guarantee")
	if allowed_companies:
		company = frappe.db.get_value(doctype, reference_name, "company")
		if company and company not in allowed_companies:
			frappe.throw(_("Not permitted for {0}").format(company), frappe.PermissionError)

	return frappe.db.get_value(doctype, reference_name, fields_to_fetch, as_dict=True)
