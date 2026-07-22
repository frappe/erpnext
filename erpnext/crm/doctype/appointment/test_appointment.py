# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import datetime
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.utils import add_to_date, getdate, now_datetime, set_request
from frappe.utils.data import sha256_hash

from erpnext.crm.doctype.appointment.appointment import (
	Appointment,
	_check_agent_availability,
	handle_expired_unverified_appointments,
)
from erpnext.setup.doctype.holiday_list.test_holiday_list import make_holiday_list
from erpnext.tests.utils import ERPNextTestSuite
from erpnext.www.book_appointment.index import create_appointment, get_appointment_slots
from erpnext.www.book_appointment.verify import index as verify_index

LEAD_EMAIL = "test_appointment_lead@example.com"
VERIFICATION_EXPIRY_MINUTES = 30
ALL_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


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


def create_lead(email, name="Existing Lead"):
	frappe.db.delete("Lead", {"email_id": email})
	return frappe.get_doc({"doctype": "Lead", "lead_name": name, "email_id": email}).insert(
		ignore_permissions=True
	)


def set_booking_setting(field, value):
	frappe.db.set_single_value("Appointment Booking Settings", field, value)


def slot_on(days_from_now, hour, minute=0):
	day = datetime.date.today() + datetime.timedelta(days=days_from_now)
	return datetime.datetime.combine(day, datetime.time(hour, minute))


def backdate_creation(appointment_name, minutes):
	frappe.db.set_value(
		"Appointment",
		appointment_name,
		"creation",
		add_to_date(now_datetime(), minutes=-minutes),
		update_modified=False,
	)


def get_status(appointment_name):
	return frappe.db.get_value("Appointment", appointment_name, "status")


def get_assignees(appointment_name):
	return frappe.parse_json(frappe.db.get_value("Appointment", appointment_name, "_assign") or "[]")


def get_todo_statuses(appointment_name):
	return frappe.get_all(
		"ToDo",
		filters={"reference_type": "Appointment", "reference_name": appointment_name},
		pluck="status",
	)


def parse_verify_url(verify_url):
	parsed = urlparse(verify_url)
	return parsed, {key: value[0] for key, value in parse_qs(parsed.query).items()}


class TestAppointment(ERPNextTestSuite):
	def setUp(self):
		set_booking_setting("verification_link_expiry_duration", VERIFICATION_EXPIRY_MINUTES)
		frappe.db.delete("Lead", {"email_id": LEAD_EMAIL})
		self.test_appointment = create_test_appointment()

	def _configure_booking_settings(self, holiday_dates=None, agents=None):
		holiday_list = make_holiday_list(
			"_Test Appointment Holiday List",
			from_date=getdate(),
			to_date=add_to_date(getdate(), days=60),
			holiday_dates=holiday_dates or [],
		)

		settings = frappe.get_doc("Appointment Booking Settings")
		settings.enable_scheduling = 1
		settings.enable_appointment_portal = 1
		settings.appointment_duration = 30
		settings.advance_booking_days = 30
		settings.verification_link_expiry_duration = VERIFICATION_EXPIRY_MINUTES
		settings.holiday_list = holiday_list.name
		settings.set("agent_list", [])
		for agent in agents or ["Administrator"]:
			settings.append("agent_list", {"user": agent})
		settings.set("availability_of_slots", [])
		for day in ALL_WEEKDAYS:
			settings.append(
				"availability_of_slots", {"day_of_week": day, "from_time": "09:00:00", "to_time": "17:00:00"}
			)
		settings.save()

	def _create_portal_appointment(self, email, days_from_now=7, time="10:00:00"):
		"""Book as Guest. The verification email is mocked and kept on
		``self._verification_email_mock`` for assertions."""
		if not getattr(self, "_booking_settings_configured", False):
			self._configure_booking_settings()
			self._booking_settings_configured = True

		with self.set_user("Guest"), patch.object(Appointment, "send_confirmation_email") as mock_send:
			appointment = create_appointment(
				date=str(datetime.date.today() + datetime.timedelta(days=days_from_now)),
				time=time,
				tz="UTC",
				contact={"name": "Portal Visitor", "email": email, "number": "123", "skype": "", "notes": ""},
			)
		self._verification_email_mock = mock_send
		return appointment

	def _request_verification(self, appointment, verify_url=None):
		"""Simulate the GET request made by clicking the emailed verification link.

		The confirmation email sent on successful verification is mocked and kept
		on ``self._confirmed_email_mock`` for assertions.
		"""
		parsed, params = parse_verify_url(verify_url or appointment._get_verify_url())

		old_request = getattr(frappe.local, "request", None)
		old_form_dict = frappe.local.form_dict
		old_user = frappe.session.user
		try:
			# the real link is clicked by an anonymous visitor; set_user resets
			# form_dict, so switch the user before populating the request
			frappe.set_user("Guest")
			set_request(method="GET", path=f"{parsed.path}?{parsed.query}")
			frappe.local.form_dict = frappe._dict(params)
			context = frappe._dict()
			with patch.object(Appointment, "send_appointment_confirmed_email") as mock_confirmed:
				verify_index.get_context(context)
			self._confirmed_email_mock = mock_confirmed
			return context
		finally:
			frappe.set_user(old_user)
			frappe.local.request = old_request
			frappe.local.form_dict = old_form_dict
			frappe.local.flags.commit = False

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
		create_lead("existing_lead@example.com")
		appointment = self._create_portal_appointment("existing_lead@example.com", days_from_now=5)

		self._verification_email_mock.assert_called_once()
		self.assertTrue(appointment.created_through_portal)
		self.assertEqual(appointment.status, "Unverified")
		self.assertFalse(appointment.email_verified)
		self.assertFalse(appointment.party)

	def test_verify_url_uses_opaque_token(self):
		appointment = self._create_portal_appointment("portal_visitor@example.com")
		parsed, params = parse_verify_url(appointment._get_verify_url())

		# the link carries only an opaque key - no email, name or signed params
		self.assertEqual(set(params), {"key"})
		self.assertNotIn("email", parsed.query)
		# only the hash of that key is stored on the appointment
		stored = frappe.db.get_value("Appointment", appointment.name, "verification_token")
		self.assertEqual(stored, sha256_hash(params["key"]))

	def test_email_verification_within_expiry_window(self):
		# Link used within the validity window - verification succeeds and the
		# appointment gets linked, assigned and added to the calendar
		on_time = self._create_portal_appointment("portal_visitor_on_time@example.com")
		context = self._request_verification(on_time)

		self.assertTrue(context.success)
		self._confirmed_email_mock.assert_called_once()
		on_time.reload()
		self.assertEqual(on_time.status, "Open")
		self.assertTrue(on_time.email_verified)
		self.assertTrue(on_time.party)
		self.assertTrue(on_time.calendar_event)

		# Link used after the validity window - verification fails
		late = self._create_portal_appointment("portal_visitor_late@example.com", days_from_now=10)
		after_expiry = add_to_date(now_datetime(), minutes=VERIFICATION_EXPIRY_MINUTES + 1)
		with patch.object(verify_index, "now_datetime", return_value=after_expiry):
			context = self._request_verification(late)

		self.assertFalse(context.success)
		self._confirmed_email_mock.assert_not_called()
		late.reload()
		self.assertEqual(late.status, "Unverified")
		self.assertFalse(late.email_verified)
		self.assertFalse(late.party)

	def test_verification_link_reused_after_success(self):
		appointment = self._create_portal_appointment("portal_visitor_twice@example.com")
		verify_url = appointment._get_verify_url()

		context = self._request_verification(appointment, verify_url=verify_url)
		self.assertTrue(context.success)
		self._confirmed_email_mock.assert_called_once()

		# re-clicking the link is idempotent and does not send another email
		context = self._request_verification(appointment, verify_url=verify_url)
		self.assertTrue(context.success)
		self.assertIn("already verified", context.message)
		self._confirmed_email_mock.assert_not_called()

	def test_verification_link_for_deleted_appointment(self):
		"""A verification link can outlive its appointment - clicking it must
		render a friendly message, not crash."""
		appointment = self._create_portal_appointment("portal_visitor_gone@example.com")
		verify_url = appointment._get_verify_url()
		frappe.delete_doc("Appointment", appointment.name, ignore_permissions=True)

		context = self._request_verification(appointment, verify_url=verify_url)

		self.assertFalse(context.success)
		self.assertIn("book the appointment again", context.message)

	def test_reschedule_syncs_calendar_event(self):
		new_time = add_to_date(self.test_appointment.scheduled_time, hours=1)
		self.test_appointment.scheduled_time = new_time
		self.test_appointment.save()

		starts_on = frappe.db.get_value("Event", self.test_appointment.calendar_event, "starts_on")
		self.assertEqual(starts_on, new_time)

	def test_portal_endpoint_disabled(self):
		self._configure_booking_settings()
		set_booking_setting("enable_appointment_portal", 0)

		with self.set_user("Guest"), self.assertRaises(frappe.Redirect):
			create_appointment(
				date=str(datetime.date.today() + datetime.timedelta(days=3)),
				time="10:00:00",
				tz="UTC",
				contact={
					"name": "Blocked",
					"email": "blocked@example.com",
					"number": "1",
					"skype": "",
					"notes": "",
				},
			)

	def test_booked_slot_unavailable_on_portal(self):
		from frappe.utils.data import get_system_timezone

		self._configure_booking_settings()
		tz = get_system_timezone()
		day = datetime.date.today() + datetime.timedelta(days=2)

		def get_availability():
			with self.set_user("Guest"):
				slots = get_appointment_slots(str(day), tz)
			return {slot["time"].strftime("%H:%M"): slot["availability"] for slot in slots}

		booked = create_test_appointment(
			customer_email="slot_taken@example.com", scheduled_time=slot_on(2, 10)
		)

		availability = get_availability()
		self.assertFalse(availability["10:00"])
		self.assertTrue(availability["13:00"])

		# closing the appointment frees its slot on the portal
		booked.status = "Closed"
		booked.save()
		self.assertTrue(get_availability()["10:00"])

		# an off-grid desk appointment blocks every portal slot it overlaps
		create_test_appointment(customer_email="off_grid@example.com", scheduled_time=slot_on(2, 13, 15))
		availability = get_availability()
		self.assertFalse(availability["13:00"])
		self.assertFalse(availability["13:30"])
		self.assertTrue(availability["14:00"])

	def test_expired_unverified_appointments_are_closed(self):
		stale = self._create_portal_appointment("portal_visitor_stale@example.com", days_from_now=8)
		fresh = self._create_portal_appointment("portal_visitor_fresh@example.com", days_from_now=9)
		verify_url = stale._get_verify_url()

		backdate_creation(stale.name, VERIFICATION_EXPIRY_MINUTES + 15)
		set_booking_setting("action_for_expired_unverified_appointments", "Mark as Closed")

		handle_expired_unverified_appointments()

		self.assertEqual(get_status(stale.name), "Closed")
		self.assertEqual(get_status(fresh.name), "Unverified")
		# Open appointments are never touched, regardless of age
		self.assertEqual(get_status(self.test_appointment.name), "Open")

		# clicking the link of a closed appointment renders a friendly message
		context = self._request_verification(stale, verify_url=verify_url)
		self.assertFalse(context.success)
		self.assertIn("closed", context.message)

	def test_expired_unverified_appointments_are_deleted(self):
		stale = self._create_portal_appointment("portal_visitor_purged@example.com", days_from_now=8)
		fresh = self._create_portal_appointment("portal_visitor_kept@example.com", days_from_now=9)

		backdate_creation(stale.name, VERIFICATION_EXPIRY_MINUTES + 15)
		set_booking_setting("action_for_expired_unverified_appointments", "Delete Permanently")

		handle_expired_unverified_appointments()

		self.assertFalse(frappe.db.exists("Appointment", stale.name))
		self.assertTrue(frappe.db.exists("Appointment", fresh.name))
		self.assertTrue(frappe.db.exists("Appointment", self.test_appointment.name))

	def test_cleanup_skipped_when_expiry_not_configured(self):
		appointment = self._create_portal_appointment("portal_visitor_no_expiry@example.com")
		backdate_creation(appointment.name, 5)
		set_booking_setting("verification_link_expiry_duration", 0)

		handle_expired_unverified_appointments()

		self.assertEqual(get_status(appointment.name), "Unverified")

	def test_status_transition_rules(self):
		# desk appointments can never be Unverified
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(customer_email="desk_unverified@example.com", status="Unverified")

		# portal appointments cannot be opened manually before verification
		unverified = self._create_portal_appointment("manual_open@example.com")
		unverified.status = "Open"
		with self.assertRaises(frappe.ValidationError):
			unverified.save(ignore_permissions=True)

		# verified appointments cannot be reverted to Unverified
		verified = self._create_portal_appointment("revert_unverified@example.com", days_from_now=8)
		self._request_verification(verified)
		verified.reload()
		verified.status = "Unverified"
		with self.assertRaises(frappe.ValidationError):
			verified.save(ignore_permissions=True)

		# both desk and verified portal appointments can be closed and reopened
		for appointment in (self.test_appointment, verified):
			appointment.reload()
			appointment.status = "Closed"
			appointment.save(ignore_permissions=True)
			appointment.status = "Open"
			appointment.save(ignore_permissions=True)
			self.assertEqual(appointment.status, "Open")

	def test_agent_auto_assignment(self):
		agent_email = "appointment_agent@example.com"
		if not frappe.db.exists("User", agent_email):
			frappe.get_doc(
				{"doctype": "User", "email": agent_email, "first_name": "Appointment Agent"}
			).insert(ignore_permissions=True)

		self._configure_booking_settings(agents=["Administrator", agent_email])
		first = create_test_appointment(
			customer_email="assigned_one@example.com", scheduled_time=slot_on(2, 11)
		)
		second = create_test_appointment(
			customer_email="assigned_two@example.com", scheduled_time=slot_on(2, 11)
		)

		# both appointments in the same slot get an agent, and never the same one
		self.assertTrue(get_assignees(first.name))
		self.assertTrue(get_assignees(second.name))
		self.assertNotEqual(get_assignees(first.name), get_assignees(second.name))

		# closing an assigned appointment closes its ToDo without re-assigning
		first.reload()
		first.status = "Closed"
		first.save()
		self.assertTrue(get_todo_statuses(first.name))
		self.assertTrue(all(status == "Closed" for status in get_todo_statuses(first.name)))

		# reopening brings the ToDos back
		first.status = "Open"
		first.save()
		self.assertTrue(all(status == "Open" for status in get_todo_statuses(first.name)))

	def test_agent_busy_for_the_whole_appointment_duration(self):
		self._configure_booking_settings()
		slot = slot_on(3, 11)
		appointment = create_test_appointment(customer_email="busy_agent@example.com", scheduled_time=slot)
		assignee = get_assignees(appointment.name)[0]

		# busy anywhere inside the 30-minute appointment window, free right after it
		self.assertFalse(_check_agent_availability(assignee, slot))
		self.assertFalse(_check_agent_availability(assignee, slot + datetime.timedelta(minutes=15)))
		self.assertTrue(_check_agent_availability(assignee, slot + datetime.timedelta(minutes=30)))

	def test_closed_appointment_closes_calendar_event(self):
		self.test_appointment.status = "Closed"
		self.test_appointment.save()
		event_status = frappe.db.get_value("Event", self.test_appointment.calendar_event, "status")
		self.assertEqual(event_status, "Closed")

		# reopening the appointment reopens the calendar event
		self.test_appointment.status = "Open"
		self.test_appointment.save()
		event_status = frappe.db.get_value("Event", self.test_appointment.calendar_event, "status")
		self.assertEqual(event_status, "Open")

	def test_deleting_appointment_deletes_calendar_event(self):
		event = self.test_appointment.calendar_event
		self.assertTrue(frappe.db.exists("Event", event))

		frappe.delete_doc("Appointment", self.test_appointment.name)

		self.assertFalse(frappe.db.exists("Event", event))

	def test_backdated_appointment_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(
				customer_email="backdated@example.com",
				scheduled_time=add_to_date(now_datetime(), hours=-1),
			)

	def test_booking_beyond_advance_window_is_rejected(self):
		self._configure_booking_settings()
		set_booking_setting("advance_booking_days", 7)

		# within the advance booking window - allowed
		within = create_test_appointment(
			customer_email="advance_within@example.com", scheduled_time=slot_on(5, 10)
		)
		self.assertTrue(frappe.db.exists("Appointment", within.name))

		# beyond the advance booking window - rejected
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(
				customer_email="advance_beyond@example.com", scheduled_time=slot_on(8, 10)
			)

	def test_appointment_on_holiday_is_rejected(self):
		holiday = add_to_date(getdate(), days=3)
		self._configure_booking_settings(
			holiday_dates=[{"holiday_date": holiday, "description": "Test Holiday"}]
		)

		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(customer_email="on_holiday@example.com", scheduled_time=slot_on(3, 10))

		# the day after the holiday is bookable
		after_holiday = create_test_appointment(
			customer_email="after_holiday@example.com", scheduled_time=slot_on(4, 10)
		)
		self.assertTrue(frappe.db.exists("Appointment", after_holiday.name))

	def test_appointment_outside_slot_timing_is_rejected(self):
		self._configure_booking_settings()

		# before the slot opens
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(customer_email="before_opening@example.com", scheduled_time=slot_on(2, 8))

		# starts within the slot but would end after it closes
		with self.assertRaises(frappe.ValidationError):
			create_test_appointment(
				customer_email="past_closing@example.com", scheduled_time=slot_on(2, 16, 45)
			)

		# within the slot timings
		within = create_test_appointment(
			customer_email="within_slot@example.com", scheduled_time=slot_on(2, 10)
		)
		self.assertTrue(frappe.db.exists("Appointment", within.name))

	def test_overlapping_time_slot_capacity(self):
		set_booking_setting("number_of_agents", 1)
		set_booking_setting("appointment_duration", 30)

		slot = slot_on(1, 10)
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
			customer_email="after_cancellation@example.com", scheduled_time=slot
		)
		self.assertTrue(frappe.db.exists("Appointment", after_cancellation.name))
