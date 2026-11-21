# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import random_string

from erpnext.crm.doctype.lead.lead import add_lead_to_prospect
from erpnext.crm.doctype.lead.test_lead import make_lead


class TestProspect(unittest.TestCase):
	def test_add_lead_to_prospect_and_address_linking(self):
		lead_doc = make_lead()
		address_doc = make_address(address_title=lead_doc.name)
		address_doc.append("links", {"link_doctype": lead_doc.doctype, "link_name": lead_doc.name})
		address_doc.save()
		prospect_doc = make_prospect()
		add_lead_to_prospect(lead_doc.name, prospect_doc.name)
		prospect_doc.reload()
		lead_exists_in_prosoect = False
		for rec in prospect_doc.get("leads"):
			if rec.lead == lead_doc.name:
				lead_exists_in_prosoect = True
		self.assertEqual(lead_exists_in_prosoect, True)
		address_doc.reload()
		self.assertEqual(address_doc.has_link("Prospect", prospect_doc.name), True)

	def test_make_customer_from_prospect(self):
		from erpnext.crm.doctype.prospect.prospect import make_customer as make_customer_from_prospect

		frappe.delete_doc_if_exists("Customer", "_Test Prospect")

		prospect = frappe.get_doc(
			{
				"doctype": "Prospect",
				"company_name": "_Test Prospect",
				"customer_group": "_Test Customer Group",
			}
		)
		prospect.insert()

		customer = make_customer_from_prospect("_Test Prospect")

		self.assertEqual(customer.doctype, "Customer")
		self.assertEqual(customer.company_name, "_Test Prospect")
		self.assertEqual(customer.customer_group, "_Test Customer Group")

		customer.company = "_Test Company"
		customer.insert()

	def test_deleting_the_only_lead_keeps_the_prospect(self):
		lead = make_lead()
		prospect = make_prospect()
		add_lead_to_prospect(lead.name, prospect.name)

		lead.delete()

		prospect.reload()
		self.assertEqual(prospect.leads, [])

	def test_lead_can_be_in_one_prospect_only_once(self):
		lead = make_lead()
		prospect = make_prospect()
		add_lead_to_prospect(lead.name, prospect.name)

		self.assertRaises(frappe.ValidationError, add_lead_to_prospect, lead.name, prospect.name)
		other = make_prospect()
		self.assertRaises(frappe.ValidationError, add_lead_to_prospect, lead.name, other.name)

	def test_lead_in_other_prospect_error_hides_a_prospect_the_user_cannot_read(self):
		lead = make_lead()
		prospect = make_prospect()
		add_lead_to_prospect(lead.name, prospect.name)

		sales_user = "test_prospect_restricted_sales_user@example.com"
		if not frappe.db.exists("User", sales_user):
			user = frappe.get_doc(
				{"doctype": "User", "email": sales_user, "first_name": "Restricted", "send_welcome_email": 0}
			)
			user.append("roles", {"role": "Sales User"})
			user.insert(ignore_permissions=True)
		frappe.permissions.add_user_permission("Prospect", make_prospect().name, sales_user)
		self.addCleanup(frappe.db.delete, "User Permission", {"user": sales_user})

		other_prospect = frappe.get_doc({"doctype": "Prospect", "leads": [{"lead": lead.name}]})
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(sales_user)
		with self.assertRaises(frappe.ValidationError) as prospect_error:
			other_prospect.validate_leads()

		self.assertNotIn(prospect.name, str(prospect_error.exception))


def make_prospect(**args):
	args = frappe._dict(args)

	prospect_doc = frappe.get_doc(
		{
			"doctype": "Prospect",
			"company_name": args.company_name or f"_Test Company {random_string(3)}",
		}
	).insert()

	return prospect_doc


def make_address(**args):
	args = frappe._dict(args)

	address_doc = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": args.address_title or "Address Title",
			"address_type": args.address_type or "Billing",
			"city": args.city or "Mumbai",
			"address_line1": args.address_line1 or "Vidya Vihar West",
			"country": args.country or "India",
		}
	).insert()

	return address_doc
