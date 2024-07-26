# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe.utils import getdate
from frappe.utils.dateutils import parse_date


@frappe.whitelist()
def upload_bank_statement():
	if getattr(frappe, "uploaded_file", None):
		with open(frappe.uploaded_file, "rb") as upfile:
			fcontent = upfile.read()
	else:
		fcontent = frappe.local.uploaded_file
		fname = frappe.local.uploaded_filename

	if frappe.safe_encode(fname).lower().endswith(b"csv"):
		from frappe.utils.csvutils import read_csv_content

		rows = read_csv_content(fcontent, False)

	elif frappe.safe_encode(fname).lower().endswith(b"xlsx"):
		from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

		rows = read_xlsx_file_from_attached_file(fcontent=fcontent)

	columns = rows[0]
	rows.pop(0)
	data = rows
	return {"columns": columns, "data": data}


@frappe.whitelist()
def create_bank_entries(columns, data, bank_account):
	header_map = get_header_mapping(columns, bank_account)

	success = 0
	errors = 0
	for d in json.loads(data):
		if all(item is None for item in d) is True:
			continue
		fields = {}
		for key, value in header_map.items():
			fields.update({key: d[int(value) - 1]})

		try:
			bank_transaction = frappe.get_doc({"doctype": "Bank Transaction"})
			bank_transaction.update(fields)
			bank_transaction.date = getdate(parse_date(bank_transaction.date))
			bank_transaction.bank_account = bank_account
			bank_transaction.insert()
			bank_transaction.submit()
			success += 1
		except Exception:
			bank_transaction.log_error("Bank entry creation failed")
			errors += 1

	return {"success": success, "errors": errors}


def get_header_mapping(columns, bank_account):
	mapping = get_bank_mapping(bank_account)

	header_map = {}
	for column in json.loads(columns):
		if column["content"] in mapping:
			header_map.update({mapping[column["content"]]: column["colIndex"]})

	return header_map


def get_bank_mapping(bank_account):
	bank_name = frappe.get_cached_value("Bank Account", bank_account, "bank")
	bank = frappe.get_doc("Bank", bank_name)

	mapping = {row.file_field: row.bank_transaction_field for row in bank.bank_transaction_mapping}

	return mapping
