# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from typing import Any, Dict, NewType, Optional

import frappe
from frappe.core.doctype.report.report import get_report_module_dotted_path

ReportFilters = Dict[str, Any]
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
	default_filters: Optional[ReportFilters] = None,
	optional_filters: Optional[ReportFilters] = None,
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

	report_execute_fn = frappe.get_attr(
		get_report_module_dotted_path(module, report_name) + ".execute"
	)
	report_filters = frappe._dict(default_filters).copy().update(filters)

	report_data = report_execute_fn(report_filters)

	if optional_filters:
		for key, value in optional_filters.items():
			filter_with_optional_param = report_filters.copy().update({key: value})
			report_execute_fn(filter_with_optional_param)

	return report_data
