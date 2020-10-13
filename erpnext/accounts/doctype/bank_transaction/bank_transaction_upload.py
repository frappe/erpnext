# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import re
from frappe.utils import getdate
from frappe.utils.dateutils import parse_date
from six import iteritems

@frappe.whitelist()
def upload_bank_statement():
	if getattr(frappe, "uploaded_file", None):
		with open(frappe.uploaded_file, "rb") as upfile:
			fcontent = upfile.read()
	else:
		fcontent = frappe.local.uploaded_file
		fname = frappe.local.uploaded_filename

	if frappe.safe_encode(fname).lower().endswith("csv".encode('utf-8')):
		from frappe.utils.csvutils import read_csv_content
		rows = read_csv_content(fcontent, False)

	elif frappe.safe_encode(fname).lower().endswith("xlsx".encode('utf-8')):
		from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
		rows = read_xlsx_file_from_attached_file(fcontent=fcontent)

	columns = rows[0]
	rows.pop(0)
	data = rows
	return {"columns": columns, "data": data}


@frappe.whitelist()
def create_bank_entries(columns, data, bank_account):
	header_map = get_header_mapping(columns, bank_account)

	default_fields = {}
	if 'currency' not in header_map:
		default_fields['currency'] = get_bank_default_currency(bank_account)

	success = 0
	errors = 0
	for d in json.loads(data):
		if all(item is None for item in d) is True:
			continue
		fields = default_fields.copy()
		for bank_field, source in iteritems(header_map):
			value = d[source[0]]
			if len(source) > 1:
				found = re.match(source[1], value)
				if not found:
					continue
				value = found.group(1)
			fields[bank_field] = value

		try:
			bank_transaction = frappe.get_doc({
				"doctype": "Bank Transaction"
			})
			bank_transaction.update(fields)
			bank_transaction.date = getdate(parse_date(bank_transaction.date))
			bank_transaction.bank_account = bank_account
			bank_transaction.insert()
			bank_transaction.submit()
			success += 1
		except Exception:
			frappe.log_error(frappe.get_traceback())
			errors += 1

	return {"success": success, "errors": errors}

def get_header_mapping(columns, bank_account):
	mapping = get_bank_mapping(bank_account)

	header_locs = {col["content"] : col["colIndex"] for col in json.loads(columns)}
	header_map = {}
	for bank_field, source in iteritems(mapping):
		if source[0] in header_locs:
			source[0] = header_locs[source[0]] - 1
			header_map[bank_field] = source

	return header_map

def get_bank_mapping(bank_account):
	bank_name = frappe.db.get_value("Bank Account", bank_account, "bank")
	bank = frappe.get_doc("Bank", bank_name)

	mapping = {}
	for row in bank.bank_transaction_mapping:
		if row.if_value_matches:
			mapping[row.bank_transaction_field] = [row.file_field, row.if_value_matches]
		else:
			mapping[row.bank_transaction_field] = [row.file_field]

	return mapping

def get_bank_default_currency(bank_account):
	company_name = frappe.db.get_value("Bank Account", bank_account, "company")
	company = frappe.get_doc("Company", company_name)
	return company.default_currency
