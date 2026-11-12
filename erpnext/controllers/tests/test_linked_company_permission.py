# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation import (
	get_reconciled_count,
)
from erpnext.accounts.doctype.subscription.test_subscription import create_plan, create_subscription
from erpnext.controllers.linked_company_permission import COMPANY_LINKS
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite

OWN_COMPANY = "_Test Company"
OTHER_COMPANY = "_Test Company 1"


class TestLinkedCompanyPermission(ERPNextTestSuite):
	"""A user restricted to one company cannot reach records that belong to another company
	only through a link, such as a Project Update of another company's Project."""

	def setUp(self):
		self.user = make_user("linked_company_restricted@example.com", ["Projects User", "Accounts User"])
		allow_company(self.user, OWN_COMPANY)

		self.own_project = make_project({"project_name": "_Test Linked Company Own", "company": OWN_COMPANY})
		self.other_project = make_project(
			{"project_name": "_Test Linked Company Other", "company": OTHER_COMPANY}
		)
		self.own_update = make_project_update(self.own_project.name)
		self.other_update = make_project_update(self.other_project.name)

	def test_list_hides_other_company_records(self):
		with self.set_user(self.user):
			names = frappe.get_list("Project Update", pluck="name")

		self.assertIn(self.own_update.name, names)
		self.assertNotIn(self.other_update.name, names)

	def test_read_is_refused_for_other_company_record(self):
		with self.set_user(self.user):
			self.assertTrue(frappe.has_permission("Project Update", "read", doc=self.own_update.name))
			self.assertFalse(frappe.has_permission("Project Update", "read", doc=self.other_update.name))

	def test_create_is_refused_for_other_company_document(self):
		with self.set_user(self.user):
			self.assertRaises(frappe.PermissionError, make_project_update, self.other_project.name)

	def test_relinking_other_company_record_is_refused(self):
		with self.set_user(self.user):
			update = frappe.get_doc("Project Update", self.other_update.name)
			update.project = self.own_project.name
			self.assertRaises(frappe.PermissionError, update.save)

	def test_unrestricted_user_sees_all_companies(self):
		user = make_user("linked_company_unrestricted@example.com", ["Projects User"])

		with self.set_user(user):
			names = frappe.get_list("Project Update", pluck="name")

		self.assertIn(self.own_update.name, names)
		self.assertIn(self.other_update.name, names)

	def test_reconciled_count_is_refused_for_other_company_run(self):
		run = frappe.new_doc("Process Payment Reconciliation")
		run.update(
			{
				"company": OTHER_COMPANY,
				"party_type": "Customer",
				"party": "_Test Customer",
				"receivable_payable_account": frappe.db.get_value(
					"Account", {"company": OTHER_COMPANY, "account_type": "Receivable", "is_group": 0}
				),
			}
		)
		run.insert()

		with self.set_user(self.user):
			self.assertRaises(frappe.PermissionError, get_reconciled_count, run.name)

	def test_bank_guarantee_without_bank_account_follows_project(self):
		own_guarantee = make_bank_guarantee(project=self.own_project.name)
		other_guarantee = make_bank_guarantee(project=self.other_project.name)

		with self.set_user(self.user):
			names = frappe.get_list("Bank Guarantee", pluck="name")
			self.assertFalse(frappe.has_permission("Bank Guarantee", "read", doc=other_guarantee.name))

		self.assertIn(own_guarantee.name, names)
		self.assertNotIn(other_guarantee.name, names)

	def test_bank_guarantee_follows_referenced_order(self):
		order = make_sales_order(
			company=OTHER_COMPANY,
			customer="_Test Customer 1",
			warehouse="_Test Warehouse 2 - _TC1",
			do_not_save=True,
		)
		order.conversion_rate = order.plc_conversion_rate = 0.02
		order.insert()
		guarantee = make_bank_guarantee(reference_doctype="Sales Order", reference_docname=order.name)

		with self.set_user(self.user):
			names = frappe.get_list("Bank Guarantee", pluck="name")
			self.assertFalse(frappe.has_permission("Bank Guarantee", "read", doc=guarantee.name))

		self.assertNotIn(guarantee.name, names)

	def test_process_subscription_skips_other_company_subscriptions(self):
		create_plan()
		create_plan(plan_name="_Test Linked Company USD Plan", currency="USD")
		own_subscription = create_subscription(company=OWN_COMPANY)
		other_subscription = create_subscription(
			company=OTHER_COMPANY,
			party="_Test Customer 1",
			plans=[{"plan": "_Test Linked Company USD Plan", "qty": 1}],
		)

		with self.set_user(self.user):
			subscriptions = frappe.new_doc("Process Subscription").get_subscriptions()

		self.assertIn(own_subscription.name, subscriptions)
		self.assertNotIn(other_subscription.name, subscriptions)

	def test_company_links_point_to_company_documents(self):
		for doctype, links in COMPANY_LINKS.items():
			meta = frappe.get_meta(doctype)
			for link in links:
				field = meta.get_field(link.fieldname)
				expected = (
					("Dynamic Link", link.doctype_fieldname)
					if link.doctype_fieldname
					else ("Link", link.doctype)
				)
				self.assertEqual((field.fieldtype, field.options), expected, doctype)
				company = frappe.get_meta(link.doctype).get_field("company")
				self.assertEqual(company.options, "Company", link.doctype)


def make_bank_guarantee(**fields):
	return frappe.get_doc(
		{
			"doctype": "Bank Guarantee",
			"bg_type": "Receiving",
			"customer": "_Test Customer",
			"amount": 1000,
			"start_date": nowdate(),
			**fields,
		}
	).insert()


def make_project_update(project):
	return frappe.get_doc(
		{"doctype": "Project Update", "project": project, "date": nowdate(), "time": "09:00:00"}
	).insert()


def make_user(email, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
	return email


def allow_company(user, company):
	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": "Company",
			"for_value": company,
			"apply_to_all_doctypes": 1,
		}
	).insert(ignore_permissions=True)
	frappe.clear_cache(user=user)
