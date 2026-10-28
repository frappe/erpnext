# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import os

import frappe
from frappe import _
from frappe.utils import get_url_to_form

DEMO_DESIGN_FILE = "steel_workbench.step"


def setup_demo_data(company_name):
	from frappe.utils.telemetry import capture

	capture("demo_data_creation_started", "erpnext")
	try:
		frappe.db.savepoint("demo_data")
		company = create_demo_company(company_name)
		process_masters()
		create_demo_design(company)
		capture("demo_data_creation_completed", "erpnext")
		frappe.clear_messages()
	except Exception:
		frappe.db.rollback(save_point="demo_data")
		error_log = frappe.log_error("Failed to create demo data")
		log_demo_data_failed_notification(error_log)
		capture("demo_data_creation_failed", "erpnext", properties={"exception": frappe.get_traceback()})


def log_demo_data_failed_notification(error_log):
	from frappe.core.doctype.role.role import get_users
	from frappe.desk.doctype.notification_log.notification_log import make_notification_logs

	frappe.msgprint(
		_("Demo data creation failed. Check notifications for more info."),
		alert=True,
		indicator="red",
		realtime=True,
	)

	notification_log = {
		"subject": _("Demo Data creation failed."),
		"type": "Alert",
		"link": get_url_to_form("Error Log", error_log.name),
	}

	make_notification_logs(notification_log, get_users("System Manager"))


def create_demo_company(company_name):
	company = frappe.get_doc("Company", company_name)

	demo_company = frappe.new_doc("Company")
	demo_company.company_name = company.company_name + " (Demo)"
	demo_company.abbr = company.abbr + "D"
	demo_company.default_currency = company.default_currency
	demo_company.country = company.country
	demo_company.chart_of_accounts_based_on = "Standard Template"
	demo_company.chart_of_accounts = company.chart_of_accounts
	demo_company.insert()

	frappe.db.set_single_value("Global Defaults", "demo_company", demo_company.name)
	return demo_company.name


def process_masters():
	for doctype in frappe.get_hooks("demo_master_doctypes"):
		for record in json.loads(read_data_file_using_hooks(doctype)):
			frappe.get_doc(record).insert(ignore_permissions=True, ignore_if_duplicate=True)


def create_demo_design(company):
	design = frappe.get_doc(
		{
			"doctype": "BOM Creator",
			"company": company,
			"item_code": "WB-1200",
			"remarks": _(
				"Steel workbench with a beech worktop, a lower shelf and a drawer on ball bearing slides."
			),
		}
	).insert()

	design.design_file = attach_demo_design_file(design.name)
	design.submit()

	for part in design.items:
		part.item_code = part.part_number

	design.save()
	design.get_bom_plan().make_boms()
	design.set_status(save=True)


def attach_demo_design_file(design_name):
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": DEMO_DESIGN_FILE,
			"content": read_demo_data_file(DEMO_DESIGN_FILE),
			"attached_to_doctype": "BOM Creator",
			"attached_to_name": design_name,
			"attached_to_field": "design_file",
			"is_private": 1,
		}
	).insert()
	return file.file_url


@frappe.whitelist()
def clear_demo_data():
	from frappe.utils.telemetry import capture

	frappe.only_for("System Manager")

	capture("demo_data_erased", "erpnext")
	try:
		company = frappe.db.get_single_value("Global Defaults", "demo_company")
		create_transaction_deletion_record(company)
		delete_company(company)
		clear_masters()
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
	return read_demo_data_file(doctype + ".json")


def read_demo_data_file(file_name):
	with open(os.path.join(os.path.dirname(__file__), "demo_data", file_name)) as f:
		return f.read()
