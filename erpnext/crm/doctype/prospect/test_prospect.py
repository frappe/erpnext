# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import random_string

from erpnext.crm.doctype.lead.lead import add_lead_to_prospect
from erpnext.crm.doctype.lead.test_lead import make_lead
from erpnext.tests.utils import ERPNextTestSuite


class TestProspect(ERPNextTestSuite):
	def test_add_lead_to_prospect_and_address_linking(self):
		company = "_Test Company"
		lead_doc = make_lead()
		address_doc = make_address(address_title=lead_doc.name)
		address_doc.append("links", {"link_doctype": lead_doc.doctype, "link_name": lead_doc.name})
		address_doc.save()
		prospect_doc = make_prospect(company=company, company_name=company)
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
				"company": "_Test Company",
			}
		)
		prospect.insert()

		customer = make_customer_from_prospect("_Test Prospect")

		self.assertEqual(customer.doctype, "Customer")
		self.assertEqual(customer.company_name, "_Test Prospect")
		self.assertEqual(customer.customer_group, "_Test Customer Group")

		customer.company = "_Test Company"
		customer.insert()

		self.assertRaises(frappe.ValidationError, make_customer_from_prospect, "_Test Prospect")

	def test_two_customer_drafts_from_one_prospect(self):
		from erpnext.crm.doctype.prospect.prospect import make_customer as make_customer_from_prospect

		prospect = make_prospect(company="_Test Company")
		first = make_customer_from_prospect(prospect.name)
		second = make_customer_from_prospect(prospect.name)

		first.insert()
		self.assertRaises(frappe.DuplicateEntryError, second.insert)

	def test_make_customer_checks_permissions_first(self):
		from erpnext.crm.doctype.prospect.prospect import make_customer as make_customer_from_prospect

		prospect = make_prospect(company="_Test Company")
		customer = make_customer_from_prospect(prospect.name)
		customer.customer_name = f"Converted {prospect.name}"
		customer.insert()

		with self.set_user(create_user("test_prospect_no_access@example.com", "Accounts User").name):
			self.assertRaises(frappe.PermissionError, make_customer_from_prospect, prospect.name)

		sales_user = create_user("test_prospect_sales_user@example.com", "Sales User").name
		frappe.permissions.add_user_permission("Customer", "_Test Customer", sales_user)
		with self.set_user(sales_user):
			with self.assertRaises(frappe.ValidationError) as error:
				make_customer_from_prospect(prospect.name)
		self.assertNotIn(customer.name, str(error.exception))

	def test_make_customer_converts_the_prospects_lead(self):
		from erpnext.crm.doctype.prospect.prospect import make_customer as make_customer_from_prospect

		lead = make_lead()
		prospect = make_prospect(company="_Test Company")
		add_lead_to_prospect(lead.name, prospect.name)

		make_customer_from_prospect(prospect.name).insert()

		self.assertEqual(frappe.db.get_value("Lead", lead.name, "status"), "Converted")

	def test_deleting_the_only_lead_keeps_the_prospect(self):
		lead = make_lead()
		prospect = make_prospect(company="_Test Company")
		add_lead_to_prospect(lead.name, prospect.name)

		lead.delete()

		prospect.reload()
		self.assertEqual(prospect.leads, [])

	def test_lead_can_be_in_one_prospect_only_once(self):
		lead = make_lead()
		prospect = make_prospect(company="_Test Company")
		add_lead_to_prospect(lead.name, prospect.name)

		self.assertRaises(frappe.ValidationError, add_lead_to_prospect, lead.name, prospect.name)
		other = make_prospect(company="_Test Company")
		self.assertRaises(frappe.ValidationError, add_lead_to_prospect, lead.name, other.name)

	def test_lead_rows_follow_the_lead_status(self):
		from erpnext.crm.doctype.lead.mapper import make_customer

		lead = make_lead()
		prospect = make_prospect(company="_Test Company")
		add_lead_to_prospect(lead.name, prospect.name)

		frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Lead",
				"party_name": lead.name,
				"company": "_Test Company",
				"items": [{"item_code": "_Test Item", "qty": 1, "rate": 100}],
			}
		).insert().submit()
		self.assertEqual(lead_row_status(lead.name), "Quotation")

		customer = make_customer(lead.name)
		customer.customer_group = "_Test Customer Group"
		customer.insert()
		self.assertEqual(lead_row_status(lead.name), "Converted")

	def test_do_not_contact_lead_is_converted_with_its_customer(self):
		from erpnext.crm.doctype.lead.mapper import make_customer

		lead = make_lead()
		lead.db_set("status", "Do Not Contact")
		prospect = make_prospect(company="_Test Company")
		add_lead_to_prospect(lead.name, prospect.name)

		customer = make_customer(lead.name)
		customer.customer_group = "_Test Customer Group"
		customer.insert()

		self.assertEqual(frappe.db.get_value("Lead", lead.name, "status"), "Converted")
		self.assertEqual(lead_row_status(lead.name), "Converted")

	def test_conversion_errors_hide_records_the_user_cannot_read(self):
		from erpnext.crm.doctype.prospect.prospect import make_customer as make_customer_from_prospect

		lead = make_lead()
		prospect = make_prospect(company="_Test Company")
		add_lead_to_prospect(lead.name, prospect.name)
		customer = make_customer_from_prospect(prospect.name)
		customer.customer_name = f"Converted {prospect.name}"
		customer.insert()

		sales_user = create_user("test_prospect_restricted_sales_user@example.com", "Sales User").name
		frappe.permissions.add_user_permission("Customer", "_Test Customer", sales_user)
		frappe.permissions.add_user_permission(
			"Prospect", make_prospect(company="_Test Company").name, sales_user
		)
		duplicate_customer = frappe.new_doc("Customer", prospect_name=prospect.name)
		other_prospect = frappe.new_doc("Prospect", leads=[{"lead": lead.name}])
		with self.set_user(sales_user):
			with self.assertRaises(frappe.DuplicateEntryError) as customer_error:
				duplicate_customer.validate_prospect_not_converted()
			with self.assertRaises(frappe.ValidationError) as prospect_error:
				other_prospect.validate_leads()

		self.assertNotIn(customer.name, str(customer_error.exception))
		self.assertNotIn(prospect.name, str(prospect_error.exception))

	def test_get_notification_email(self):
		admin_email = frappe.db.get_value("User", "Administrator", "email")
		prospect = frappe.new_doc("Prospect")
		prospect.prospect_owner = "Administrator"
		self.assertEqual(prospect.get_notification_email(), admin_email)

		prospect.prospect_owner = None
		self.assertIsNone(prospect.get_notification_email())


def lead_row_status(lead: str) -> str:
	return frappe.db.get_value("Prospect Lead", {"lead": lead}, "status")


def make_prospect(**args):
	args = frappe._dict(args)

	prospect_doc = frappe.get_doc(
		{
			"doctype": "Prospect",
			"company_name": args.company_name or f"_Test Company {random_string(3)}",
			"company": args.company,
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
