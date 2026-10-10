# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import unittest

import frappe
from frappe.utils import random_string, today

from erpnext.crm.doctype.lead.lead import make_opportunity
from erpnext.crm.utils import get_linked_prospect
from erpnext.tests.utils import ERPNextTestSuite


class TestLead(ERPNextTestSuite):
	def test_make_customer(self):
		from erpnext.crm.doctype.lead.lead import make_customer

		lead = frappe.db.get_all("Lead", {"lead_name": "_Test Lead"})[0].name

		frappe.delete_doc_if_exists("Customer", "_Test Lead")

		customer = make_customer(lead)
		self.assertEqual(customer.doctype, "Customer")
		self.assertEqual(customer.lead_name, lead)

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

	def test_customer_from_lead_keeps_records_the_user_cannot_write(self):
		from erpnext.buying.test_utils import create_user_with_roles
		from erpnext.crm.doctype.lead.lead import make_customer
		from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity

		user = "_test_lead_master_manager@example.com"
		create_user_with_roles(user, "Sales Master Manager")
		lead = make_lead()
		opportunity = make_opportunity(opportunity_from="Lead", lead=lead.name)
		customer = make_customer(lead.name)

		with self.set_user(user):
			customer.insert()

		self.assertEqual(frappe.db.get_value("Opportunity", opportunity.name, "opportunity_from"), "Lead")

	def test_customer_from_lead_takes_over_its_quotations_and_opportunities(self):
		from erpnext.crm.doctype.lead.lead import make_customer
		from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity
		from erpnext.selling.doctype.quotation.test_quotation import make_quotation

		lead = make_lead()
		opportunity = make_opportunity(opportunity_from="Lead", lead=lead.name)
		quotation = make_quotation(do_not_save=1)
		quotation.quotation_to = "Lead"
		quotation.party_name = lead.name
		quotation.insert()
		quotation.submit()

		customer = make_customer(lead.name).insert()

		self.assertEqual(
			frappe.db.get_value("Quotation", quotation.name, ["quotation_to", "party_name"]),
			("Customer", customer.name),
		)
		self.assertEqual(
			frappe.db.get_value("Opportunity", opportunity.name, ["opportunity_from", "party_name"]),
			("Customer", customer.name),
		)

	def test_make_customer_from_organization(self):
		from erpnext.crm.doctype.lead.lead import make_customer

		lead = frappe.db.get_all("Lead", {"lead_name": "_Test Lead 1"})[0].name
		customer = make_customer(lead)
		self.assertEqual(customer.doctype, "Customer")
		self.assertEqual(customer.lead_name, lead)

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
		opportunity.company = "_Test Company"
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

	def test_set_lead_name_fallbacks(self):
		# organization name is used when there is no person name
		lead = frappe.new_doc("Lead")
		lead.company_name = "_Test Org Lead"
		lead.set_lead_name()
		self.assertEqual(lead.lead_name, "_Test Org Lead")

		# the email local-part is used when only an email is present
		lead = frappe.new_doc("Lead")
		lead.email_id = "jane.doe@example.com"
		lead.set_lead_name()
		self.assertEqual(lead.lead_name, "jane.doe")

		# data import (ignore_mandatory) with no name/company/email must not crash
		lead = frappe.new_doc("Lead")
		lead.flags.ignore_mandatory = True
		lead.set_lead_name()
		self.assertFalse(lead.lead_name)

		# otherwise a lead with no name source is rejected
		lead = frappe.new_doc("Lead")
		self.assertRaises(frappe.ValidationError, lead.set_lead_name)


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
