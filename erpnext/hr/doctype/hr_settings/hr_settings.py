# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import format_date

# Wether to proceed with frequency change
PROCEED_WITH_FREQUENCY_CHANGE = False

class HRSettings(Document):
	def validate(self):
		self.set_naming_series()

		# Based on proceed flag
		global PROCEED_WITH_FREQUENCY_CHANGE
		if not PROCEED_WITH_FREQUENCY_CHANGE:
			self.validate_frequency_change()
		PROCEED_WITH_FREQUENCY_CHANGE = False

	def set_naming_series(self):
		from erpnext.setup.doctype.naming_series.naming_series import set_by_naming_series
		set_by_naming_series("Employee", "employee_number",
			self.get("emp_created_by")=="Naming Series", hide_name_field=True)

	def validate_frequency_change(self):
		weekly_job, monthly_job = None, None

		try:
			weekly_job = frappe.get_doc(
				'Scheduled Job Type',
				'employee_reminders.send_reminders_in_advance_weekly'
			)

			monthly_job = frappe.get_doc(
				'Scheduled Job Type',
				'employee_reminders.send_reminders_in_advance_monthly'
			)
		except frappe.DoesNotExistError:
			return

		next_weekly_trigger = weekly_job.get_next_execution()
		next_monthly_trigger = monthly_job.get_next_execution()

		if self.freq_changed_from_monthly_to_weekly():
			if next_monthly_trigger < next_weekly_trigger:
				self.show_freq_change_warning(next_monthly_trigger, next_weekly_trigger)

		elif self.freq_changed_from_weekly_to_monthly():
			if next_monthly_trigger > next_weekly_trigger:
				self.show_freq_change_warning(next_weekly_trigger, next_monthly_trigger)

	def freq_changed_from_weekly_to_monthly(self):
		return self.has_value_changed("frequency") and self.frequency == "Monthly"

	def freq_changed_from_monthly_to_weekly(self):
		return self.has_value_changed("frequency") and self.frequency == "Weekly"

	def show_freq_change_warning(self, from_date, to_date):
		from_date = frappe.bold(format_date(from_date))
		to_date = frappe.bold(format_date(to_date))
		frappe.msgprint(
			msg=frappe._('Employees will miss holiday reminders from {} until {}. <br> Do you want to proceed with this change?').format(from_date, to_date),
			title='Confirm change in Frequency',
			primary_action={
				'label': frappe._('Yes, Proceed'),
				'client_action': 'erpnext.proceed_save_with_reminders_frequency_change'
			},
			raise_exception=frappe.ValidationError
		)

@frappe.whitelist()
def set_proceed_with_frequency_change():
	'''Enables proceed with frequency change'''
	global PROCEED_WITH_FREQUENCY_CHANGE
	PROCEED_WITH_FREQUENCY_CHANGE = True
