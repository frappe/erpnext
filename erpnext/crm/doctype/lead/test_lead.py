# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.utils import random_string, today

from erpnext.crm.doctype.lead.lead import make_opportunity
from erpnext.crm.utils import get_linked_prospect

test_records = frappe.get_test_records("Lead")


class TestLead(unittest.TestCase):
	def test_make_customer(self):
		from erpnext.crm.doctype.lead.lead import make_customer

		frappe.delete_doc_if_exists("Customer", "_Test Lead")

		customer = make_customer("_T-Lead-00001")
		self.assertEqual(customer.doctype, "Customer")
		self.assertEqual(customer.lead_name, "_T-Lead-00001")

		customer.company = "_Test Company"
		customer.customer_group = "_Test Customer Group"
		customer.insert()

		# check whether lead contact is carried forward to the customer.
		contact = frappe.db.get_value(
			"Dynamic Link",
			{
				"parenttype": "Contact",
				"link_doctype": "Lead",
				"link_name": customer.lead_name,
			},
			"parent",
		)

		if contact:
			contact_doc = frappe.get_doc("Contact", contact)
			self.assertEqual(contact_doc.has_link(customer.doctype, customer.name), True)

	def test_make_customer_from_organization(self):
		from erpnext.crm.doctype.lead.lead import make_customer

		customer = make_customer("_T-Lead-00002")
		self.assertEqual(customer.doctype, "Customer")
		self.assertEqual(customer.lead_name, "_T-Lead-00002")

		customer.company = "_Test Company"
		customer.customer_group = "_Test Customer Group"
		customer.insert()

	def test_create_lead_and_unlinking_dynamic_links(self):
		lead_doc = make_lead(first_name="Lorem", last_name="Ipsum", email_id="lorem_ipsum@example.com")
		lead_doc_1 = make_lead()
		frappe.get_doc(
			{
				"doctype": "Address",
				"address_type": "Billing",
				"city": "Mumbai",
				"address_line1": "Vidya Vihar West",
				"country": "India",
				"links": [{"link_doctype": "Lead", "link_name": lead_doc.name}],
			}
		).insert()

		address_1 = frappe.get_doc(
			{
				"doctype": "Address",
				"address_type": "Billing",
				"address_line1": "Baner",
				"city": "Pune",
				"country": "India",
				"links": [
					{"link_doctype": "Lead", "link_name": lead_doc.name},
					{"link_doctype": "Lead", "link_name": lead_doc_1.name},
				],
			}
		).insert()

		lead_doc.delete()
		address_1.reload()
		self.assertEqual(frappe.db.exists("Lead", lead_doc.name), None)
		self.assertEqual(len(address_1.get("links")), 1)

	def test_prospect_creation_from_lead(self):
		frappe.db.sql("delete from `tabLead` where lead_name='Rahul Tripathi'")
		frappe.db.sql("delete from `tabProspect` where name='Prospect Company'")

		lead = make_lead(
			first_name="Rahul",
			last_name="Tripathi",
			email_id="rahul@gmail.com",
			company_name="Prospect Company",
		)

		event = create_event("Meeting 1", today(), "Lead", lead.name)

		lead.create_prospect(lead.company_name)

		prospect = get_linked_prospect("Lead", lead.name)
		self.assertEqual(prospect, "Prospect Company")

		event.reload()
		self.assertEqual(event.event_participants[1].reference_doctype, "Prospect")
		self.assertEqual(event.event_participants[1].reference_docname, prospect)

	def test_opportunity_from_lead(self):
		frappe.db.sql("delete from `tabLead` where lead_name='Rahul Tripathi'")
		frappe.db.sql("delete from `tabOpportunity` where party_name='Rahul Tripathi'")

		lead = make_lead(
			first_name="Rahul",
			last_name="Tripathi",
			email_id="rahul@gmail.com",
			company_name="Prospect Company",
		)

		lead.add_note("test note")
		event = create_event("Meeting 1", today(), "Lead", lead.name)
		create_todo("followup", "Lead", lead.name)

		opportunity = make_opportunity(lead.name)
		opportunity.save()

		self.assertEqual(opportunity.get("party_name"), lead.name)
		self.assertEqual(opportunity.notes[0].note, "test note")

		event.reload()
		self.assertEqual(event.event_participants[1].reference_doctype, "Opportunity")
		self.assertEqual(event.event_participants[1].reference_docname, opportunity.name)

		self.assertTrue(
			frappe.db.get_value("ToDo", {"reference_type": "Opportunity", "reference_name": opportunity.name})
		)

	def test_copy_events_from_lead_to_prospect(self):
		frappe.db.sql("delete from `tabLead` where lead_name='Rahul Tripathi'")
		frappe.db.sql("delete from `tabProspect` where name='Prospect Company'")

		lead = make_lead(
			first_name="Rahul",
			last_name="Tripathi",
			email_id="rahul@gmail.com",
			company_name="Prospect Company",
		)

		lead.create_prospect(lead.company_name)
		prospect = get_linked_prospect("Lead", lead.name)

		event = create_event("Meeting", today(), "Lead", lead.name)

		self.assertEqual(len(event.event_participants), 2)
		self.assertEqual(event.event_participants[1].reference_doctype, "Prospect")
		self.assertEqual(event.event_participants[1].reference_docname, prospect)


def create_event(subject, starts_on, reference_type, reference_name):
	event = frappe.new_doc("Event")
	event.subject = subject
	event.starts_on = starts_on
	event.event_type = "Private"
	event.all_day = 1
	event.owner = "Administrator"
	event.append(
		"event_participants", {"reference_doctype": reference_type, "reference_docname": reference_name}
	)
	event.reference_type = reference_type
	event.reference_name = reference_name
	event.insert()
	return event


def create_todo(description, reference_type, reference_name):
	todo = frappe.new_doc("ToDo")
	todo.description = description
	todo.owner = "Administrator"
	todo.reference_type = reference_type
	todo.reference_name = reference_name
	todo.insert()
	return todo


def make_lead(**args):
	args = frappe._dict(args)

	lead_doc = frappe.get_doc(
		{
			"doctype": "Lead",
			"first_name": args.first_name or "_Test",
			"last_name": args.last_name or "Lead",
			"email_id": args.email_id or f"new_lead_{random_string(5)}@example.com",
			"company_name": args.company_name or "_Test Company",
		}
	).insert()

	return lead_doc
