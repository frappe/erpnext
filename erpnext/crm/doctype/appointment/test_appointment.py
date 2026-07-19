# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import datetime
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.utils import add_to_date, get_datetime, getdate, now_datetime, set_request

from erpnext.crm.doctype.appointment.appointment import (
	Appointment,
	delete_expired_unverified_appointments,
)
from erpnext.setup.doctype.holiday_list.test_holiday_list import make_holiday_list
from erpnext.tests.utils import ERPNextTestSuite
from erpnext.www.book_appointment.index import create_appointment
from erpnext.www.book_appointment.verify import index as verify_index

LEAD_EMAIL = "test_appointment_lead@example.com"
VERIFICATION_EXPIRY_MINUTES = 30


def create_test_appointment(**kwargs):
	args = {
		"doctype": "Appointment",
		"status": "Open",
		"customer_name": "Test Lead",
		"customer_phone_number": "666",
		"customer_skype": "test",
		"customer_email": LEAD_EMAIL,
		"scheduled_time": add_to_date(now_datetime(), hours=2),
		"customer_details": "Hello, Friend!",
	}
	args.update(kwargs)
	test_appointment = frappe.get_doc(args)
	test_appointment.insert()
	return test_appointment


class TestAppointment(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value(
			"Appointment Booking Settings", "verification_link_expiry_duration", VERIFICATION_EXPIRY_MINUTES
		)
		frappe.db.delete("Lead", {"email_id": LEAD_EMAIL})
		self.test_appointment = create_test_appointment()

	def test_calendar_event_created(self):
		cal_event = frappe.get_doc("Event", self.test_appointment.calendar_event)
		self.assertEqual(cal_event.starts_on, self.test_appointment.scheduled_time)

	def test_lead_linked(self):
		self.assertTrue(self.test_appointment.party)

	def test_desk_created_appointment_skips_email_verification(self):
		"""Appointments created from the desk (created_through_portal unset) must be
		linked and confirmed immediately - no verification email should be sent."""
		with patch.object(Appointment, "send_confirmation_email") as mock_send:
			appointment = create_test_appointment(customer_email="another_desk_lead@example.com")

		mock_send.assert_not_called()
		self.assertEqual(appointment.status, "Open")
		self.assertTrue(appointment.party)
		frappe.db.delete("Lead", {"email_id": "another_desk_lead@example.com"})

	def test_portal_booking_stays_unverified_for_existing_lead(self):
		"""A portal booking whose email matches an existing Lead/Customer must NOT
		be auto-linked - it must stay Unverified until the email is confirmed."""
		existing_lead_email = "existing_lead@example.com"
		frappe.db.delete("Lead", {"email_id": existing_lead_email})
		frappe.get_doc(
			{"doctype": "Lead", "lead_name": "Existing Lead", "email_id": existing_lead_email}
		).insert(ignore_permissions=True)

		frappe.db.set_single_value("Appointment Booking Settings", "enable_scheduling", 1)
		frappe.db.set_single_value("Appointment Booking Settings", "number_of_agents", 0)

		with self.set_user("Guest"), patch.object(Appointment, "send_confirmation_email") as mock_send:
			appointment = create_appointment(
				date=str(datetime.date.today() + datetime.timedelta(days=5)),
				time="10:00:00",
				tz="UTC",
				contact={
					"name": "Portal Visitor",
					"email": existing_lead_email,
					"number": "123",
					"skype": "",
					"notes": "",
				},
			)

		mock_send.assert_called_once()
		self.assertTrue(appointment.created_through_portal)
		self.assertEqual(appointment.status, "Unverified")
		self.assertFalse(appointment.party)

	def test_portal_booking_links_party_only_after_email_verification(self):
		"""Only after the confirmation link is used does the appointment get linked
		to the matching Lead and confirmed. This also covers saving the verified
		appointment as a Guest user, which must not raise a PermissionError."""
		existing_lead_email = "another_existing_lead@example.com"
		frappe.db.delete("Lead", {"email_id": existing_lead_email})
		frappe.get_doc(
			{"doctype": "Lead", "lead_name": "Another Existing Lead", "email_id": existing_lead_email}
		).insert(ignore_permissions=True)

		frappe.db.set_single_value("Appointment Booking Settings", "enable_scheduling", 1)
		frappe.db.set_single_value("Appointment Booking Settings", "number_of_agents", 0)

		with self.set_user("Guest"), patch.object(Appointment, "send_confirmation_email"):
			appointment = create_appointment(
				date=str(datetime.date.today() + datetime.timedelta(days=6)),
				time="11:00:00",
				tz="UTC",
				contact={
					"name": "Portal Visitor",
					"email": existing_lead_email,
					"number": "123",
					"skype": "",
					"notes": "",
				},
			)

			appointment.set_verified(existing_lead_email)
			appointment.save(ignore_permissions=True)

		self.assertEqual(appointment.status, "Open")
		self.assertTrue(appointment.party)

	def _create_portal_appointment(self, email, days_from_now=7, time="10:00:00"):
		frappe.db.set_single_value("Appointment Booking Settings", "enable_scheduling", 1)
		frappe.db.set_single_value("Appointment Booking Settings", "number_of_agents", 0)
		frappe.db.set_single_value("Appointment Booking Settings", "advance_booking_days", 30)

		with self.set_user("Guest"), patch.object(Appointment, "send_confirmation_email"):
			return create_appointment(
				date=str(datetime.date.today() + datetime.timedelta(days=days_from_now)),
				time=time,
				tz="UTC",
				contact={"name": "Portal Visitor", "email": email, "number": "123", "skype": "", "notes": ""},
			)

	def test_verify_url_contains_expiry(self):
		appointment = self._create_portal_appointment("portal_visitor@example.com")

		query = urlparse(appointment._get_verify_url()).query
		params = {key: value[0] for key, value in parse_qs(query).items()}

		self.assertIn("_signature", params)
		self.assertIn("valid_till", params)
		valid_till = get_datetime(params["valid_till"])
		self.assertGreater(valid_till, add_to_date(now_datetime(), minutes=VERIFICATION_EXPIRY_MINUTES - 1))
		self.assertLessEqual(valid_till, add_to_date(now_datetime(), minutes=VERIFICATION_EXPIRY_MINUTES + 1))

	def _request_verification(self, appointment, verify_url=None):
		"""Simulate the GET request made by clicking the emailed verification link."""
		parsed = urlparse(verify_url or appointment._get_verify_url())
		params = {key: value[0] for key, value in parse_qs(parsed.query).items()}

		old_request = getattr(frappe.local, "request", None)
		old_form_dict = frappe.local.form_dict
		try:
			set_request(method="GET", path=f"{parsed.path}?{parsed.query}")
			frappe.local.form_dict = frappe._dict(params)
			context = frappe._dict()
			verify_index.get_context(context)
			return context
		finally:
			frappe.local.request = old_request
			frappe.local.form_dict = old_form_dict
			frappe.local.flags.commit = False

	def test_email_verification_within_expiry_window(self):
		# Link used within the validity window - verification succeeds
		on_time = self._create_portal_appointment("portal_visitor_on_time@example.com")
		context = self._request_verification(on_time)

		self.assertTrue(context.success)
		on_time.reload()
		self.assertEqual(on_time.status, "Open")
		self.assertTrue(on_time.party)

		# Link used after the validity window - verification fails
		late = self._create_portal_appointment("portal_visitor_late@example.com", days_from_now=10)
		after_expiry = add_to_date(now_datetime(), minutes=VERIFICATION_EXPIRY_MINUTES + 1)
		with patch.object(verify_index, "now_datetime", return_value=after_expiry):
			context = self._request_verification(late)

		self.assertFalse(context.success)
		late.reload()
		self.assertEqual(late.status, "Unverified")
		self.assertFalse(late.party)

	def test_verification_link_for_deleted_appointment(self):
		"""A signed link can outlive its appointment (the cleanup job deletes stale
		Unverified appointments) - clicking it must render the expired message, not crash."""
		appointment = self._create_portal_appointment("portal_visitor_gone@example.com")
		verify_url = appointment._get_verify_url()
		frappe.delete_doc("Appointment", appointment.name, ignore_permissions=True)

		context = self._request_verification(appointment, verify_url=verify_url)

		self.assertFalse(context.success)
		self.assertIn("expired", context.message)

	def test_expired_unverified_appointments_are_deleted(self):
		stale = self._create_portal_appointment("portal_visitor_stale@example.com", days_from_now=8)
		fresh = self._create_portal_appointment("portal_visitor_fresh@example.com", days_from_now=9)

		frappe.db.set_value(
			"Appointment",
			stale.name,
			"creation",
			add_to_date(now_datetime(), minutes=-(VERIFICATION_EXPIRY_MINUTES + 15)),
			update_modified=False,
		)

		delete_expired_unverified_appointments()

		self.assertFalse(frappe.db.exists("Appointment", stale.name))
		self.assertTrue(frappe.db.exists("Appointment", fresh.name))
		# Open appointments are never touched, regardless of age
		self.assertTrue(frappe.db.exists("Appointment", self.test_appointment.name))

	def test_cleanup_skipped_when_expiry_not_configured(self):
		appointment = self._create_portal_appointment("portal_visitor_no_expiry@example.com")
		frappe.db.set_value(
			"Appointment",
			appointment.name,
			"creation",
			add_to_date(now_datetime(), minutes=-5),
			update_modified=False,
		)
		frappe.db.set_single_value("Appointment Booking Settings", "verification_link_expiry_duration", 0)

		delete_expired_unverified_appointments()

		self.assertTrue(frappe.db.exists("Appointment", appointment.name))

	def test_booking_beyond_advance_window_is_rejected(self):
		frappe.db.set_single_value("Appointment Booking Settings", "advance_booking_days", 7)

		# within the advance booking window - allowed
		within = create_test_appointment(
			customer_email="advance_within@example.com",
			scheduled_time=add_to_date(now_datetime(), days=5),
		)
		self.assertTrue(frappe.db.exists("Appointment", within.name))

		# beyond the advance booking window - rejected
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(
				customer_email="advance_beyond@example.com",
				scheduled_time=add_to_date(now_datetime(), days=8),
			)

	def test_overlapping_time_slot_capacity(self):
		frappe.db.set_single_value("Appointment Booking Settings", "number_of_agents", 1)
		frappe.db.set_single_value("Appointment Booking Settings", "appointment_duration", 30)

		slot = datetime.datetime.combine(
			datetime.date.today() + datetime.timedelta(days=1), datetime.time(10, 0)
		)
		first = create_test_appointment(customer_email="slot_first@example.com", scheduled_time=slot)

		# a booking starting inside the first appointment's duration is rejected
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(
				customer_email="slot_overlap@example.com",
				scheduled_time=slot + datetime.timedelta(minutes=15),
			)

		# rescheduling must not count the appointment's own booked slot
		first.scheduled_time = slot + datetime.timedelta(minutes=10)
		first.save()

		# a booking starting exactly when the rescheduled one ends is allowed
		adjacent = create_test_appointment(
			customer_email="slot_adjacent@example.com",
			scheduled_time=slot + datetime.timedelta(minutes=40),
		)
		self.assertTrue(frappe.db.exists("Appointment", adjacent.name))

		# a closed (cancelled) appointment frees its slot
		first.status = "Closed"
		first.save()
		after_cancellation = create_test_appointment(
			customer_email="after_cancellation@example.com",
			scheduled_time=slot,
		)
		self.assertTrue(frappe.db.exists("Appointment", after_cancellation.name))

	def _configure_slot_settings(self, holiday_dates=None):
		holiday_list = make_holiday_list(
			"_Test Appointment Holiday List",
			from_date=getdate(),
			to_date=add_to_date(getdate(), days=60),
			holiday_dates=holiday_dates or [],
		)

		settings = frappe.get_doc("Appointment Booking Settings")
		settings.enable_scheduling = 1
		settings.appointment_duration = 30
		settings.advance_booking_days = 30
		settings.holiday_list = holiday_list.name
		settings.set("agent_list", [])
		settings.append("agent_list", {"user": "Administrator"})
		settings.set("availability_of_slots", [])
		for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
			settings.append(
				"availability_of_slots", {"day_of_week": day, "from_time": "09:00:00", "to_time": "17:00:00"}
			)
		settings.save()

	def test_backdated_appointment_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(
				customer_email="backdated@example.com",
				scheduled_time=add_to_date(now_datetime(), hours=-1),
			)

	def test_appointment_on_holiday_is_rejected(self):
		holiday = add_to_date(getdate(), days=3)
		self._configure_slot_settings(
			holiday_dates=[{"holiday_date": holiday, "description": "Test Holiday"}]
		)

		scheduled = datetime.datetime.combine(holiday, datetime.time(10, 0))
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(customer_email="on_holiday@example.com", scheduled_time=scheduled)

		# the day after the holiday is bookable
		after_holiday = create_test_appointment(
			customer_email="after_holiday@example.com",
			scheduled_time=scheduled + datetime.timedelta(days=1),
		)
		self.assertTrue(frappe.db.exists("Appointment", after_holiday.name))

	def test_appointment_outside_slot_timing_is_rejected(self):
		self._configure_slot_settings()
		day = datetime.date.today() + datetime.timedelta(days=2)

		# before the slot opens
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(
				customer_email="before_opening@example.com",
				scheduled_time=datetime.datetime.combine(day, datetime.time(8, 0)),
			)

		# starts within the slot but would end after it closes
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(
				customer_email="past_closing@example.com",
				scheduled_time=datetime.datetime.combine(day, datetime.time(16, 45)),
			)

		# within the slot timings
		within = create_test_appointment(
			customer_email="within_slot@example.com",
			scheduled_time=datetime.datetime.combine(day, datetime.time(10, 0)),
		)
		self.assertTrue(frappe.db.exists("Appointment", within.name))
