# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, add_years, date_diff, get_last_day, getdate


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
		lease_payment_schedule: DF.Table[LeasePaymentSchedule]
		lease_start_date: DF.Date
		lease_term_months: DF.Int
		leased_asset: DF.Link
		naming_series: DF.Literal["LA-.YYYY.-.#####."]
		payment_frequency: DF.Literal["Monthly", "Yearly"]
		periodic_lease_amount: DF.Currency
		status: DF.Literal["Draft", "Active", "Closed", "Cancelled"]
		supplier: DF.Link
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
		if self.docstatus != 0:
			return

		if self.schedule_inputs_changed():
			self.regenerate_schedule()

	def set_lease_end_date(self):
		if self.use_lease_term and self.lease_start_date and self.lease_term_months:
			end_date = add_months(self.lease_start_date, int(self.lease_term_months))
			self.lease_end_date = add_days(end_date, -1)

	def schedule_inputs_changed(self):
		if not self.get("_doc_before_save"):
			return True

		old = self.get("_doc_before_save")

		fields = [
			"lease_start_date",
			"lease_end_date",
			"periodic_lease_amount",
			"payment_frequency",
		]

		for field in fields:
			if old.get(field) != self.get(field):
				return True

		return False

	def regenerate_schedule(self):
		self.lease_payment_schedule = []
		self.build_schedule()

	def on_submit(self):
		if self.schedule_inputs_changed():
			self.lease_payment_schedule = []
			self.build_schedule()

	def build_schedule(self):
		self.schedule = []

		if self.payment_frequency == "Monthly":
			self.build_monthly_schedule()
		else:
			self.build_yearly_schedule()

	def build_monthly_schedule(self):
		start_date = getdate(self.lease_start_date)
		end_date = getdate(self.lease_end_date)

		current_start = start_date

		while current_start <= end_date:
			period_end = get_last_day(current_start)

			if period_end > end_date:
				period_end = end_date

			total_days = date_diff(get_last_day(current_start), current_start.replace(day=1)) + 1
			chargeable_days = date_diff(period_end, current_start) + 1

			amount = self.periodic_lease_amount * (chargeable_days / total_days)

			self.append("lease_payment_schedule", {"schedule_date": period_end, "amount": round(amount, 2)})

			current_start = add_months(current_start.replace(day=1), 1)

	def build_yearly_schedule(self):
		start_date = getdate(self.lease_start_date)
		end_date = getdate(self.lease_end_date)

		current_start = start_date

		while current_start <= end_date:
			period_end = get_last_day(current_start.replace(month=12))

			if period_end > end_date:
				period_end = end_date

			year_start = current_start.replace(month=1, day=1)
			year_end = get_last_day(year_start.replace(month=12))

			total_days = date_diff(year_end, year_start) + 1
			chargeable_days = date_diff(period_end, current_start) + 1

			amount = self.periodic_lease_amount * (chargeable_days / total_days)

			self.append("lease_payment_schedule", {"schedule_date": period_end, "amount": round(amount, 2)})

			current_start = add_years(current_start.replace(month=1, day=1), 1)
