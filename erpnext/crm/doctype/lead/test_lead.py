# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.utils import random_string

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


def make_lead(**args):
	args = frappe._dict(args)

	lead_doc = frappe.get_doc(
		{
			"doctype": "Lead",
			"first_name": args.first_name or "_Test",
			"last_name": args.last_name or "Lead",
			"email_id": args.email_id or "new_lead_{}@example.com".format(random_string(5)),
		}
	).insert()

	return lead_doc
