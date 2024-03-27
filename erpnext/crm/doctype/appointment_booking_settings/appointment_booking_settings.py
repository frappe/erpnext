# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import datetime
import typing

import frappe
from frappe import _
from frappe.model.document import Document


class AppointmentBookingSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.automation.doctype.assignment_rule_user.assignment_rule_user import (
			AssignmentRuleUser,
		)
		from frappe.types import DF

		from erpnext.crm.doctype.appointment_booking_slots.appointment_booking_slots import (
			AppointmentBookingSlots,
		)

		advance_booking_days: DF.Int
		agent_list: DF.TableMultiSelect[AssignmentRuleUser]
		appointment_duration: DF.Int
		availability_of_slots: DF.Table[AppointmentBookingSlots]
		email_reminders: DF.Check
		enable_scheduling: DF.Check
		holiday_list: DF.Link
		number_of_agents: DF.Int
		success_redirect_url: DF.Data | None
	# end: auto-generated types

	agent_list: typing.ClassVar[list] = []  # Hack
	min_date = "01/01/1970 "
	format_string = "%d/%m/%Y %H:%M:%S"

	def validate(self):
		self.validate_availability_of_slots()

	def save(self):
		self.number_of_agents = len(self.agent_list)
		super().save()

	def validate_availability_of_slots(self):
		for record in self.availability_of_slots:
			from_time = datetime.datetime.strptime(self.min_date + record.from_time, self.format_string)
			to_time = datetime.datetime.strptime(self.min_date + record.to_time, self.format_string)
			to_time - from_time
			self.validate_from_and_to_time(from_time, to_time, record)
			self.duration_is_divisible(from_time, to_time)

	def validate_from_and_to_time(self, from_time, to_time, record):
		if from_time > to_time:
			err_msg = _("<b>From Time</b> cannot be later than <b>To Time</b> for {0}").format(
				record.day_of_week
			)
			frappe.throw(_(err_msg))

	def duration_is_divisible(self, from_time, to_time):
		timedelta = to_time - from_time
		if timedelta.total_seconds() % (self.appointment_duration * 60):
			frappe.throw(_("The difference between from time and To Time must be a multiple of Appointment"))
