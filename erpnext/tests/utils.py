# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from typing import Any, NewType

import frappe
from frappe.core.doctype.report.report import get_report_module_dotted_path
from frappe.tests import IntegrationTestCase

ReportFilters = dict[str, Any]
ReportName = NewType("ReportName", str)


def create_test_contact_and_address():
	frappe.db.sql("delete from tabContact")
	frappe.db.sql("delete from `tabContact Email`")
	frappe.db.sql("delete from `tabContact Phone`")
	frappe.db.sql("delete from tabAddress")
	frappe.db.sql("delete from `tabDynamic Link`")

	frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": "_Test Address for Customer",
			"address_type": "Office",
			"address_line1": "Station Road",
			"city": "_Test City",
			"state": "Test State",
			"country": "India",
			"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
		}
	).insert()

	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": "_Test Contact for _Test Customer",
			"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
		}
	)
	contact.add_email("test_contact_customer@example.com", is_primary=True)
	contact.add_phone("+91 0000000000", is_primary_phone=True)
	contact.insert()

	contact_two = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": "_Test Contact 2 for _Test Customer",
			"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
		}
	)
	contact_two.add_email("test_contact_two_customer@example.com", is_primary=True)
	contact_two.add_phone("+92 0000000000", is_primary_phone=True)
	contact_two.insert()


def execute_script_report(
	report_name: ReportName,
	module: str,
	filters: ReportFilters,
	default_filters: ReportFilters | None = None,
	optional_filters: ReportFilters | None = None,
):
	"""Util for testing execution of a report with specified filters.

	Tests the execution of report with default_filters + filters.
	Tests the execution using optional_filters one at a time.

	Args:
	        report_name: Human readable name of report (unscrubbed)
	        module: module to which report belongs to
	        filters: specific values for filters
	        default_filters: default values for filters such as company name.
	        optional_filters: filters which should be tested one at a time in addition to default filters.
	"""

	if default_filters is None:
		default_filters = {}

	test_filters = []
	report_execute_fn = frappe.get_attr(get_report_module_dotted_path(module, report_name) + ".execute")
	report_filters = frappe._dict(default_filters).copy().update(filters)

	test_filters.append(report_filters)

	if optional_filters:
		for key, value in optional_filters.items():
			test_filters.append(report_filters.copy().update({key: value}))

	for test_filter in test_filters:
		try:
			report_execute_fn(test_filter)
		except Exception:
			print(f"Report failed to execute with filters: {test_filter}")
			raise


def if_lending_app_installed(function):
	"""Decorator to check if lending app is installed"""

	def wrapper(*args, **kwargs):
		if "lending" in frappe.get_installed_apps():
			return function(*args, **kwargs)
		return

	return wrapper


def if_lending_app_not_installed(function):
	"""Decorator to check if lending app is not installed"""

	def wrapper(*args, **kwargs):
		if "lending" not in frappe.get_installed_apps():
			return function(*args, **kwargs)
		return

	return wrapper


class ERPNextTestSuite(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

	@classmethod
	def make_monthly_distribution(cls):
		records = [
			{
				"doctype": "Monthly Distribution",
				"distribution_id": "_Test Distribution",
				"fiscal_year": "_Test Fiscal Year 2013",
				"percentages": [
					{"month": "January", "percentage_allocation": "8"},
					{"month": "February", "percentage_allocation": "8"},
					{"month": "March", "percentage_allocation": "8"},
					{"month": "April", "percentage_allocation": "8"},
					{"month": "May", "percentage_allocation": "8"},
					{"month": "June", "percentage_allocation": "8"},
					{"month": "July", "percentage_allocation": "8"},
					{"month": "August", "percentage_allocation": "8"},
					{"month": "September", "percentage_allocation": "8"},
					{"month": "October", "percentage_allocation": "8"},
					{"month": "November", "percentage_allocation": "10"},
					{"month": "December", "percentage_allocation": "10"},
				],
			}
		]
		cls.monthly_distribution = []
		for x in records:
			if not frappe.db.exists("Monthly Distribution", {"distribution_id": x.get("distribution_id")}):
				cls.monthly_distribution.append(frappe.get_doc(x).insert())
			else:
				cls.monthly_distribution.append(
					frappe.get_doc("Monthly Distribution", {"distribution_id": x.get("distribution_id")})
				)

	@classmethod
	def make_projects(cls):
		records = [
			{
				"doctype": "Project",
				"company": "_Test Company",
				"project_name": "_Test Project",
				"status": "Open",
			}
		]

		cls.projects = []
		for x in records:
			if not frappe.db.exists("Project", {"project_name": x.get("project_name")}):
				cls.projects.append(frappe.get_doc(x).insert())
			else:
				cls.projects.append(frappe.get_doc("Project", {"project_name": x.get("project_name")}))

	@classmethod
	def make_employees(cls):
		records = [
			{
				"company": "_Test Company",
				"date_of_birth": "1980-01-01",
				"date_of_joining": "2010-01-01",
				"department": "_Test Department - _TC",
				"doctype": "Employee",
				"first_name": "_Test Employee",
				"gender": "Female",
				"naming_series": "_T-Employee-",
				"status": "Active",
				"user_id": "test@example.com",
			},
			{
				"company": "_Test Company",
				"date_of_birth": "1980-01-01",
				"date_of_joining": "2010-01-01",
				"department": "_Test Department 1 - _TC",
				"doctype": "Employee",
				"first_name": "_Test Employee 1",
				"gender": "Male",
				"naming_series": "_T-Employee-",
				"status": "Active",
				"user_id": "test1@example.com",
			},
			{
				"company": "_Test Company",
				"date_of_birth": "1980-01-01",
				"date_of_joining": "2010-01-01",
				"department": "_Test Department 1 - _TC",
				"doctype": "Employee",
				"first_name": "_Test Employee 2",
				"gender": "Male",
				"naming_series": "_T-Employee-",
				"status": "Active",
				"user_id": "test2@example.com",
			},
		]
		cls.employees = []
		for x in records:
			if not frappe.db.exists("Employee", {"first_name": x.get("first_name")}):
				cls.employees.append(frappe.get_doc(x).insert())
			else:
				cls.employees.append(frappe.get_doc("Employee", {"first_name": x.get("first_name")}))

	@classmethod
	def make_sales_person(cls):
		records = [
			{
				"doctype": "Sales Person",
				"employee": "_T-Employee-00001",
				"is_group": 0,
				"parent_sales_person": "Sales Team",
				"sales_person_name": "_Test Sales Person",
			},
			{
				"doctype": "Sales Person",
				"employee": "_T-Employee-00002",
				"is_group": 0,
				"parent_sales_person": "Sales Team",
				"sales_person_name": "_Test Sales Person 1",
			},
			{
				"doctype": "Sales Person",
				"employee": "_T-Employee-00003",
				"is_group": 0,
				"parent_sales_person": "Sales Team",
				"sales_person_name": "_Test Sales Person 2",
			},
		]
		cls.sales_person = []
		for x in records:
			if not frappe.db.exists("Sales Person", {"sales_person_name": x.get("sales_person_name")}):
				cls.sales_person.append(frappe.get_doc(x).insert())
			else:
				cls.sales_person.append(
					frappe.get_doc("Sales Person", {"sales_person_name": x.get("sales_person_name")})
				)

	@classmethod
	def make_leads(cls):
		records = [
			{
				"doctype": "Lead",
				"email_id": "test_lead@example.com",
				"lead_name": "_Test Lead",
				"status": "Open",
				"territory": "_Test Territory",
				"naming_series": "_T-Lead-",
			},
			{
				"doctype": "Lead",
				"email_id": "test_lead1@example.com",
				"lead_name": "_Test Lead 1",
				"status": "Open",
				"naming_series": "_T-Lead-",
			},
			{
				"doctype": "Lead",
				"email_id": "test_lead2@example.com",
				"lead_name": "_Test Lead 2",
				"status": "Lead",
				"naming_series": "_T-Lead-",
			},
			{
				"doctype": "Lead",
				"email_id": "test_lead3@example.com",
				"lead_name": "_Test Lead 3",
				"status": "Converted",
				"naming_series": "_T-Lead-",
			},
			{
				"doctype": "Lead",
				"email_id": "test_lead4@example.com",
				"lead_name": "_Test Lead 4",
				"company_name": "_Test Lead 4",
				"status": "Open",
				"naming_series": "_T-Lead-",
			},
		]
		cls.leads = []
		for x in records:
			if not frappe.db.exists("Lead", {"email_id": x.get("email_id")}):
				cls.leads.append(frappe.get_doc(x).insert())
			else:
				cls.leads.append(frappe.get_doc("Lead", {"email_id": x.get("email_id")}))
