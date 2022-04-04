# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import datetime
import unittest

import frappe


def create_test_lead():
	test_lead = frappe.db.exists({"doctype": "Lead", "lead_name": "Test Lead"})
	if test_lead:
		return frappe.get_doc("Lead", test_lead[0][0])
	test_lead = frappe.get_doc(
		{"doctype": "Lead", "lead_name": "Test Lead", "email_id": "test@example.com"}
	)
	test_lead.insert(ignore_permissions=True)
	return test_lead


def create_test_appointments():
	test_appointment = frappe.db.exists(
		{
			"doctype": "Appointment",
			"scheduled_time": datetime.datetime.now(),
			"email": "test@example.com",
		}
	)
	if test_appointment:
		return frappe.get_doc("Appointment", test_appointment[0][0])
	test_appointment = frappe.get_doc(
		{
			"doctype": "Appointment",
			"email": "test@example.com",
			"status": "Open",
			"customer_name": "Test Lead",
			"customer_phone_number": "666",
			"customer_skype": "test",
			"customer_email": "test@example.com",
			"scheduled_time": datetime.datetime.now(),
		}
	)
	test_appointment.insert()
	return test_appointment


class TestAppointment(unittest.TestCase):
	test_appointment = test_lead = None

	def setUp(self):
		self.test_lead = create_test_lead()
		self.test_appointment = create_test_appointments()

	def test_calendar_event_created(self):
		cal_event = frappe.get_doc("Event", self.test_appointment.calendar_event)
		self.assertEqual(cal_event.starts_on, self.test_appointment.scheduled_time)

	def test_lead_linked(self):
		lead = frappe.get_doc("Lead", self.test_lead.name)
		self.assertIsNotNone(lead)
