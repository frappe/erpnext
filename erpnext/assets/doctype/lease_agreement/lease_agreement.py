# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LeaseAgreement(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.lease_payment_schedule.lease_payment_schedule import LeasePaymentSchedule

		amended_from: DF.Link | None
		company: DF.Link
		lease_amount: DF.Currency
		lease_end_date: DF.Date
		lease_expense_account: DF.Link
		lease_liability_account: DF.Link
		lease_start_date: DF.Date
		leased_asset: DF.Link
		naming_series: DF.Literal["LA-.YYYY.-.#####."]
		payment_frequency: DF.Literal["Monthly"]
		status: DF.Literal["Draft", "Active", "Closed", "Cancelled"]
		supplier: DF.Link
		table_jilb: DF.Table[LeasePaymentSchedule]
	# end: auto-generated types

	pass
