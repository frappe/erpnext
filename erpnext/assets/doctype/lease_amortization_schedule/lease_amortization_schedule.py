# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LeaseAmortizationSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.lease_payment_schedule.lease_payment_schedule import LeasePaymentSchedule

		amended_from: DF.Link | None
		generated_on: DF.Date | None
		lease_agreement: DF.Link
		lease_type: DF.Literal["Finance", "Operating"]
		table_orqo: DF.Table[LeasePaymentSchedule]
		total_interest: DF.Currency
		total_payment: DF.Currency
		total_periods: DF.Int
		total_principal: DF.Currency
	# end: auto-generated types

	pass
