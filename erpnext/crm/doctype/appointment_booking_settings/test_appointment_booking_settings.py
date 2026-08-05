# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import datetime

import frappe
from frappe.utils import add_to_date, getdate

from erpnext.setup.doctype.holiday_list.test_holiday_list import make_holiday_list
from erpnext.tests.utils import ERPNextTestSuite


class TestAppointmentBookingSettings(ERPNextTestSuite):
	def assert_invalid(self, settings):
		with self.assertRaises(frappe.ValidationError):
			settings.save()

	def make_settings(self, appointment_duration=30):
		doc = frappe.new_doc("Appointment Booking Settings")
		doc.appointment_duration = appointment_duration
		return doc

	def dt(self, hms):
		# the controller parses times against a fixed epoch date
		return datetime.datetime.strptime("1970-01-01 " + hms, "%Y-%m-%d %H:%M:%S")

	def get_valid_scheduling_settings(self):
		holiday_list = make_holiday_list(
			"_Test Booking Settings Holiday List",
			from_date=getdate(),
			to_date=add_to_date(getdate(), days=30),
			holiday_dates=[],
		)

		settings = frappe.get_doc("Appointment Booking Settings")
		settings.enable_scheduling = 1
		settings.appointment_duration = 30
		settings.advance_booking_days = 7
		settings.verification_link_expiry_duration = 30
		settings.holiday_list = holiday_list.name
		settings.set("agent_list", [])
		settings.append("agent_list", {"user": "Administrator"})
		settings.set("availability_of_slots", [])
		settings.append(
			"availability_of_slots",
			{"day_of_week": "Monday", "from_time": "09:00:00", "to_time": "17:00:00"},
		)
		return settings

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

	def test_scheduling_requires_slots(self):
		settings = self.get_valid_scheduling_settings()
		settings.set("availability_of_slots", [])

		self.assert_invalid(settings)

	def test_validate_checks_every_slot(self):
		settings = self.get_valid_scheduling_settings()
		settings.append(
			"availability_of_slots",
			{"day_of_week": "Tuesday", "from_time": "09:00:00", "to_time": "09:45:00"},
		)

		self.assert_invalid(settings)

	def test_scheduling_requires_holiday_list_covering_today(self):
		settings = self.get_valid_scheduling_settings()
		settings.holiday_list = None
		self.assert_invalid(settings)

		expired_list = make_holiday_list(
			"_Test Booking Settings Expired Holiday List",
			from_date=add_to_date(getdate(), days=-60),
			to_date=add_to_date(getdate(), days=-30),
			holiday_dates=[],
		)
		settings.holiday_list = expired_list.name
		self.assert_invalid(settings)

	def test_scheduling_requires_advance_booking_days(self):
		settings = self.get_valid_scheduling_settings()
		settings.advance_booking_days = 0

		self.assert_invalid(settings)

	def test_portal_requires_scheduling(self):
		settings = frappe.get_doc("Appointment Booking Settings")
		settings.enable_scheduling = 0
		settings.enable_appointment_portal = 1

		self.assert_invalid(settings)

	def test_portal_expiry_duration_bounds(self):
		settings = self.get_valid_scheduling_settings()
		settings.enable_appointment_portal = 1
		settings.verification_link_expiry_duration = 5

		self.assert_invalid(settings)

	def test_number_of_agents_derived_from_agent_list(self):
		settings = self.get_valid_scheduling_settings()
		settings.number_of_agents = 99
		settings.save()

		self.assertEqual(frappe.db.get_single_value("Appointment Booking Settings", "number_of_agents"), 1)
