# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import datetime

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestAppointmentBookingSettings(ERPNextTestSuite):
	"""The settings validate each availability slot: from-time must precede to-time and
	the slot length must be a whole multiple of the appointment duration."""

	def make_settings(self, appointment_duration=30):
		doc = frappe.new_doc("Appointment Booking Settings")
		doc.appointment_duration = appointment_duration
		return doc

	def dt(self, hms):
		# the controller parses times against a fixed epoch date
		return datetime.datetime.strptime("01/01/1970 " + hms, "%d/%m/%Y %H:%M:%S")

	def test_from_time_must_precede_to_time(self):
		doc = self.make_settings()
		record = frappe._dict(day_of_week="Monday")
		self.assertRaises(
			frappe.ValidationError,
			doc.validate_from_and_to_time,
			self.dt("18:00:00"),
			self.dt("09:00:00"),
			record,
		)
		doc.validate_from_and_to_time(self.dt("09:00:00"), self.dt("18:00:00"), record)  # valid order

	def test_slot_length_must_be_a_multiple_of_the_duration(self):
		doc = self.make_settings(appointment_duration=30)
		# 60 minutes is two 30-minute appointments -> fine
		doc.duration_is_divisible(self.dt("09:00:00"), self.dt("10:00:00"))
		# 45 minutes leaves a partial appointment -> rejected
		self.assertRaises(
			frappe.ValidationError, doc.duration_is_divisible, self.dt("09:00:00"), self.dt("09:45:00")
		)

	def test_validate_checks_every_slot(self):
		bad = self.make_settings(appointment_duration=30)
		bad.append(
			"availability_of_slots",
			{"day_of_week": "Monday", "from_time": "09:00:00", "to_time": "09:45:00"},
		)
		self.assertRaises(frappe.ValidationError, bad.validate)

		# a clean 60-minute slot passes end to end
		good = self.make_settings(appointment_duration=30)
		good.append(
			"availability_of_slots",
			{"day_of_week": "Monday", "from_time": "09:00:00", "to_time": "10:00:00"},
		)
		good.validate()
