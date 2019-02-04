# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, csv, os
from frappe import _
from frappe.utils import cstr
from frappe.model.document import Document
from frappe.utils.csvutils import UnicodeWriter
from frappe.utils.file_manager import get_file_path
from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import create_charts, build_tree_from_json

class ChartofAccountsImporter(Document):
	pass

@frappe.whitelist()
def validate_company(company):
	if frappe.db.get_all('GL Entry', {"company": company}, "name", limit=1):
		return False	

@frappe.whitelist()
def import_coa(file_name, company):
	# delete existing data for accounts
	frappe.db.sql('''delete from `tabAccount` where company="%s"''' % company, debug=1)

	# create accounts
	create_charts(company, custom_chart=generate_data_from_csv(file_name))

def generate_data_from_csv(file_name):
	''' read csv file and return the generated nested tree '''
	file_path = get_file_path(file_name)

	data = []
	with open(file_path, 'r') as in_file:
		csv_reader = list(csv.reader(in_file))
		headers = csv_reader[1][1:]
		del csv_reader[0:2] # delete top row and headers row

		for row in csv_reader:
			if not row[2]: row[2] = row[1]
			data.append(row[1:])

	# convert csv data to a child-parent structure
	forest = {}
	return forest

@frappe.whitelist()
def download_template():
	data = frappe._dict(frappe.local.form_dict)
	fields = ["Account Name", "Parent Account", "Is Group", "Account Type", "Root Type"]
	writer = UnicodeWriter()

	writer.writerow([_('Chart of Accounts Template')])
	writer.writerow([_("Column Labels : ")] + fields)
	writer.writerow([_("Start entering data from here : ")])

	# download csv file
	frappe.response['result'] = cstr(writer.getvalue())
	frappe.response['type'] = 'csv'
	frappe.response['doctype'] = data.get('doctype')
