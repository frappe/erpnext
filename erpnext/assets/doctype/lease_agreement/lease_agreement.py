# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months


class LeaseAgreement(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.lease_payment_schedule.lease_payment_schedule import LeasePaymentSchedule

		amended_from: DF.Link | None
		company: DF.Link
		lease_end_date: DF.Date
		lease_expense_account: DF.Link
		lease_start_date: DF.Date
		lease_term_months: DF.Int
		leased_asset: DF.Link
		naming_series: DF.Literal["LA-.YYYY.-.#####."]
		payment_frequency: DF.Literal["Monthly", "Yearly"]
		periodic_lease_amount: DF.Currency
		status: DF.Literal["Draft", "Active", "Closed", "Cancelled"]
		supplier: DF.Link
		table_jilb: DF.Table[LeasePaymentSchedule]
		use_lease_term: DF.Check
	# end: auto-generated types

	def validate(self):
		self.validate_lease_dates()

	def validate_lease_dates(self):
		if self.lease_start_date and self.lease_end_date:
			if self.lease_end_date < self.lease_start_date:
				frappe.throw(
					_("Lease End Date cannot be before Lease Start Date."),
					title=_("Invalid Lease Dates"),
				)

	def before_save(self):
		self.set_lease_end_date()

	def set_lease_end_date(self):
		if self.use_lease_term and self.lease_start_date and self.lease_term_months:
			end_date = add_months(self.lease_start_date, int(self.lease_term_months))
			self.lease_end_date = add_days(end_date, -1)
