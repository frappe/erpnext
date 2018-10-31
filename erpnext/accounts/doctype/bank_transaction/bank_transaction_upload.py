# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.utils import getdate

@frappe.whitelist()
def upload_bank_statement():
	if getattr(frappe, "uploaded_file", None):
		with open(frappe.uploaded_file, "rb") as upfile:
			fcontent = upfile.read()
	else:
		from frappe.utils.file_manager import get_uploaded_content
		fname, fcontent = get_uploaded_content()

	if frappe.safe_encode(fname).lower().endswith("csv"):
		from frappe.utils.csvutils import read_csv_content
		rows = read_csv_content(fcontent, False)

	elif frappe.safe_encode(fname).lower().endswith("xlsx"):
		from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
		rows = read_xlsx_file_from_attached_file(fcontent=fcontent)

	columns = rows[0]
	rows.pop(0)
	data = rows
	return {"columns": columns, "data": data}


@frappe.whitelist()
def create_bank_entries(columns, data, bank_account):
	bank_account = json.loads(bank_account)
	header_map = get_header_mapping(columns, bank_account)

	for d in json.loads(data):
		fields = {}
		for key, value in header_map.iteritems():
			fields.update({key: d[int(value)-1]})


		bank_transaction = frappe.get_doc({
			"doctype": "Bank Transaction"
		})
		bank_transaction.update(fields)
		bank_transaction.date = getdate(bank_transaction.date)
		bank_transaction.bank_account = bank_account["name"]
		bank_transaction.insert()

	return 'success'

def get_header_mapping(columns, bank_account):
	mapping = get_bank_mapping(bank_account)

	header_map = {}
	for column in json.loads(columns):
		if column["content"] in mapping:
			header_map.update({mapping[column["content"]]: column["colIndex"]})

	return header_map

def get_bank_mapping(bank_account):
	bank_name = frappe.db.get_value("Bank Account", bank_account["name"], "bank")
	bank = frappe.get_doc("Bank", bank_name)

	mapping = {row.file_field:row.bank_transaction_field for row in bank.bank_transaction_mapping}

	return mapping