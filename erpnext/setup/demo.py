# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import os

import frappe
from frappe import _


@frappe.whitelist()
def clear_demo_data():
	from frappe.utils.telemetry import capture

	frappe.only_for("System Manager")

	capture("demo_data_erased", "erpnext")
	try:
		company = frappe.db.get_single_value("Global Defaults", "demo_company")
		create_transaction_deletion_record(company)
		clear_masters()
		delete_company(company)
		default_company = frappe.db.get_single_value("Global Defaults", "default_company")
		frappe.db.set_default("company", default_company)
	except Exception:
		frappe.db.rollback()
		frappe.log_error("Failed to erase demo data")
		frappe.throw(
			_("Failed to erase demo data, please delete the demo company manually."),
			title=_("Could Not Delete Demo Data"),
		)


def create_transaction_deletion_record(company):
	transaction_deletion_record = frappe.new_doc("Transaction Deletion Record")
	transaction_deletion_record.company = company
	transaction_deletion_record.process_in_single_transaction = True
	transaction_deletion_record.save(ignore_permissions=True)

	transaction_deletion_record.generate_to_delete_list()
	transaction_deletion_record.reload()

	transaction_deletion_record.submit()
	transaction_deletion_record.start_deletion_tasks()


def clear_masters():
	for doctype in frappe.get_hooks("demo_master_doctypes")[::-1]:
		data = read_data_file_using_hooks(doctype)
		if data:
			for item in json.loads(data):
				clear_demo_record(item)


def clear_demo_record(document):
	document_type = document.get("doctype")
	del document["doctype"]

	valid_columns = frappe.get_meta(document_type).get_valid_columns()

	filters = document
	for key in list(filters):
		if key not in valid_columns:
			filters.pop(key, None)

	try:
		doc = frappe.get_doc(document_type, filters)
		doc.delete(ignore_permissions=True)
	except frappe.exceptions.DoesNotExistError:
		pass


def delete_company(company):
	frappe.db.set_single_value("Global Defaults", "demo_company", "")
	frappe.delete_doc("Company", company, ignore_permissions=True)


def read_data_file_using_hooks(doctype):
	path = os.path.join(os.path.dirname(__file__), "demo_data")
	with open(os.path.join(path, doctype + ".json")) as f:
		data = f.read()

	return data
