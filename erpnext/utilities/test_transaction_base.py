# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import now_datetime, random_string

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.transaction_base import delete_events


class TestDeleteEvents(ERPNextTestSuite):
	def _make_event(self, reference_doctype, reference_docname):
		# Insert a bare Event, then attach the Event Participants child row directly.
		# reference_docname is a Dynamic Link that would otherwise be validated against a
		# real target doc on save; db_insert keeps the test self-contained with arbitrary
		# (random, guaranteed-unique) docnames while still populating exactly the columns
		# delete_events joins/filters on (parent, reference_doctype, reference_docname).
		event = frappe.get_doc(
			{
				"doctype": "Event",
				"subject": "Test Event " + random_string(10),
				"starts_on": now_datetime(),
				"event_type": "Private",
			}
		).insert(ignore_permissions=True)

		participant = frappe.new_doc("Event Participants")
		participant.name = frappe.generate_hash(length=10)
		participant.flags.name_set = True
		participant.parent = event.name
		participant.parenttype = "Event"
		participant.parentfield = "event_participants"
		participant.idx = 1
		participant.reference_doctype = reference_doctype
		participant.reference_docname = reference_docname
		participant.db_insert()

		return event.name

	def test_delete_events_removes_matching_and_keeps_others(self):
		# Two distinct, real reference_docnames so the filter has something to discriminate on.
		match_name = "Match " + random_string(10)
		other_name = "Other " + random_string(10)
		event_match = self._make_event("Customer", match_name)
		event_other = self._make_event("Customer", other_name)

		# Sanity: both exist before deletion (otherwise the assertions below are tautological).
		self.assertTrue(frappe.db.exists("Event", event_match))
		self.assertTrue(frappe.db.exists("Event", event_other))

		delete_events("Customer", match_name)

		# Only the Event whose participant matches BOTH reference_doctype and
		# reference_docname must be deleted.
		self.assertFalse(frappe.db.exists("Event", event_match))
		self.assertTrue(frappe.db.exists("Event", event_other))

	def test_delete_events_no_match_is_noop(self):
		# When nothing matches, no Event may be deleted.
		event = self._make_event("Customer", "Present " + random_string(10))
		self.assertTrue(frappe.db.exists("Event", event))

		delete_events("Customer", "Absent " + random_string(10))

		self.assertTrue(frappe.db.exists("Event", event))

	def test_delete_events_distinguishes_reference_doctype(self):
		# Same docname under two different reference_doctypes: only the queried doctype
		# is deleted, proving both predicates are ANDed together.
		shared_name = "Shared " + random_string(10)
		event_customer = self._make_event("Customer", shared_name)
		event_supplier = self._make_event("Supplier", shared_name)

		delete_events("Customer", shared_name)

		self.assertFalse(frappe.db.exists("Event", event_customer))
		self.assertTrue(frappe.db.exists("Event", event_supplier))
