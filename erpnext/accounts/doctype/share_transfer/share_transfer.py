# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.exceptions import ValidationError
from frappe.model.document import Document


class ShareDontExists(ValidationError):
	pass


class ShareTransfer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount: DF.Currency
		asset_account: DF.Link | None
		company: DF.Link
		date: DF.Date
		equity_or_liability_account: DF.Link
		from_folio_no: DF.Data | None
		from_no: DF.Int
		from_shareholder: DF.Link | None
		no_of_shares: DF.Int
		rate: DF.Currency
		remarks: DF.LongText | None
		share_type: DF.Link
		to_folio_no: DF.Data | None
		to_no: DF.Int
		to_shareholder: DF.Link | None
		transfer_type: DF.Literal["", "Issue", "Purchase", "Transfer"]
	# end: auto-generated types

	def validate(self):
		frappe.throw(_("Share Transfer is read-only. Create a Share Transaction instead."))

	before_insert = validate
	before_submit = validate
	before_cancel = validate
	before_update_after_submit = validate
	on_trash = validate
	on_submit = validate
	on_cancel = validate


@frappe.whitelist(methods=["POST"])
def make_jv_entry(
	company: str,
	account: str,
	amount: float,
	payment_account: str,
	credit_applicant_type: str,
	credit_applicant: str,
	debit_applicant_type: str,
	debit_applicant: str,
):
	frappe.throw(_("Share Transfer is read-only. Create a Share Transaction instead."))
