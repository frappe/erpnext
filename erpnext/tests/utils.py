# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import copy
import sys
from contextlib import contextmanager
from typing import Any, Dict, NewType, Optional

import frappe
from frappe.core.doctype.report.report import get_report_module_dotted_path
from frappe.modules import load_doctype_module

ReportFilters = Dict[str, Any]
ReportName = NewType("ReportName", str)


def create_test_contact_and_address():
	frappe.db.sql('delete from tabContact')
	frappe.db.sql('delete from `tabContact Email`')
	frappe.db.sql('delete from `tabContact Phone`')
	frappe.db.sql('delete from tabAddress')
	frappe.db.sql('delete from `tabDynamic Link`')

	frappe.get_doc({
		"doctype": "Address",
		"address_title": "_Test Address for Customer",
		"address_type": "Office",
		"address_line1": "Station Road",
		"city": "_Test City",
		"state": "Test State",
		"country": "India",
		"links": [
			{
				"link_doctype": "Customer",
				"link_name": "_Test Customer"
			}
		]
	}).insert()

	contact = frappe.get_doc({
		"doctype": 'Contact',
		"first_name": "_Test Contact for _Test Customer",
		"links": [
			{
				"link_doctype": "Customer",
				"link_name": "_Test Customer"
			}
		]
	})
	contact.add_email("test_contact_customer@example.com", is_primary=True)
	contact.add_phone("+91 0000000000", is_primary_phone=True)
	contact.insert()


@contextmanager
def change_settings(doctype, settings_dict):
	""" A context manager to ensure that settings are changed before running
	function and restored after running it regardless of exceptions occured.
	This is useful in tests where you want to make changes in a function but
	don't retain those changes.
	import and use as decorator to cover full function or using `with` statement.

	example:
	@change_settings("Stock Settings", {"item_naming_by": "Naming Series"})
	def test_case(self):
		...
	"""

	try:
		settings = frappe.get_doc(doctype)
		# remember setting
		previous_settings = copy.deepcopy(settings_dict)
		for key in previous_settings:
			previous_settings[key] = getattr(settings, key)

		# change setting
		for key, value in settings_dict.items():
			setattr(settings, key, value)
		settings.save()
		yield # yield control to calling function

	finally:
		# restore settings
		settings = frappe.get_doc(doctype)
		for key, value in previous_settings.items():
			setattr(settings, key, value)
		settings.save()


def execute_script_report(
		report_name: ReportName,
		module: str,
		filters: ReportFilters,
		default_filters: Optional[ReportFilters] = None,
		optional_filters: Optional[ReportFilters] = None
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

	report_execute_fn = frappe.get_attr(get_report_module_dotted_path(module, report_name) + ".execute")
	report_filters = frappe._dict(default_filters).copy().update(filters)

	report_data = report_execute_fn(report_filters)

	if optional_filters:
		for key, value in optional_filters.items():
			filter_with_optional_param = report_filters.copy().update({key: value})
			report_execute_fn(filter_with_optional_param)

	return report_data


def find_missing_indexes():

	doctypes_to_check = [
		"Item",
		"Stock Ledger Entry",
		"GL Entry",
		"Material Request Item",
		"Packed Item",
		"Bin",
		"Account",
		"Purchase Invoice",
		"Sales Invoice",
		"Work Order Item",
	]
	missing_indexes = []

	for doctype in doctypes_to_check:
		index_before = frappe.db.sql(f"show index from `tab{doctype}`", as_dict=1)

		doctype_module = load_doctype_module(doctype)
		getattr(doctype_module, "on_doctype_update")()
		index_after = frappe.db.sql(f"show index from `tab{doctype}`", as_dict=1)

		missing_indexes.extend(
			[f"{doctype}.{index}" for index in _compare_indexes(index_before, index_after)]
		)

	if missing_indexes:
		print("Expected following indexes to exist")
		print("\n".join(missing_indexes))
		sys.exit(1)


def _compare_indexes(before, after):
	key_names_before = {i["Key_name"] for i in before}
	key_names_after = {i["Key_name"] for i in after}
	return key_names_after - key_names_before
