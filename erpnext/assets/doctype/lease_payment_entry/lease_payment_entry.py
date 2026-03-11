# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LeasePaymentEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_payment: DF.Currency
		amended_from: DF.Link | None
		bank_account: DF.Link | None
		deferred_rent: DF.Currency
		gst_amount: DF.Currency
		gst_journal_entry: DF.Link | None
		interest: DF.Currency
		journal_entry: DF.Link | None
		lease_agreement: DF.Link | None
		lease_type: DF.Data | None
		net_payable: DF.Currency
		payment_date: DF.Date | None
		principal_amount: DF.Currency
		purchase_invoice: DF.Link | None
		schedule_row: DF.Data | None
		straight_line_expense: DF.Currency
		tds_amount: DF.Currency
	# end: auto-generated types

	pass
