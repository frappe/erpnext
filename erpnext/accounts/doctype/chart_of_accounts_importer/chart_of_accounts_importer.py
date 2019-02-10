# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, csv
from frappe import _
from frappe.utils import cstr
from frappe.model.document import Document
from frappe.utils.csvutils import UnicodeWriter
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
	unset_existing_data(company)

	# create accounts
	forest = build_forest(generate_data_from_csv(file_name))
	create_charts(company, custom_chart=forest)

	# trigger on_update for company to reset default accounts
	set_default_accounts(company)

def generate_data_from_csv(file_name, as_dict=False):
	''' read csv file and return the generated nested tree '''
	file_doc = frappe.get_doc('File', {"file_url": file_name})
	file_path = file_doc.get_full_path()

	data = []
	with open(file_path, 'r') as in_file:
		csv_reader = list(csv.reader(in_file))
		headers = csv_reader[1][1:]
		del csv_reader[0:2] # delete top row and headers row

		for row in csv_reader:
			if as_dict:
				data.append({frappe.scrub(header): row[index+1] for index, header in enumerate(headers)})
			else:
				if not row[2]: row[2] = row[1]
				data.append(row[1:])

	# convert csv data
	return data

@frappe.whitelist()
def get_coa(doctype, parent, is_root=False, file_name=None):
	''' called by tree view (to fetch node's children) '''

	parent = None if parent==_('All Accounts') else parent
	forest = build_forest(generate_data_from_csv(file_name))
	accounts = build_tree_from_json("", chart_data=forest) # returns alist of dict in a tree render-able form

	# filter out to show data for the selected node only
	accounts = [d for d in accounts if d['parent_account']==parent]

	return accounts

def build_forest(data):
	'''
		converts list of list into a nested tree
		if a = [[1,1], [1,2], [3,2], [4,4], [5,4]]
		tree = {
			1: {
				2: {
					3: {}
				}
			},
			4: {
				5: {}
			}
		}
	'''

	# set the value of nested dictionary
	def set_nested(d, path, value):
		reduce(lambda d, k: d.setdefault(k, {}), path[:-1], d)[path[-1]] = value
		return d

	# returns the path of any node in list format
	def return_parent(data, child):
		for row in data:
			account_name, parent_account = row[0:2]
			if parent_account == account_name == child:
				return [parent_account]
			elif account_name == child:
				return [child] + return_parent(data, parent_account)

	charts_map, paths = {}, []
	for i in data:
		account_name, _, is_group, account_type, root_type = i
		charts_map[account_name] = {}
		if is_group: charts_map[account_name]["is_group"] = is_group
		if account_type: charts_map[account_name]["account_type"] = account_type
		if root_type: charts_map[account_name]["root_type"] = root_type
		path = return_parent(data, account_name)[::-1]
		paths.append(path) # List of path is created

	out = {}
	for path in paths:
		for n, account_name in enumerate(path):
			set_nested(out, path[:n+1], charts_map[account_name]) # setting the value of nested dictionary.

	return out

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

@frappe.whitelist()
def validate_accounts(file_name):
	accounts = generate_data_from_csv(file_name, as_dict=True)

	accounts_dict = {}
	for account in accounts:
		accounts_dict.setdefault(account["account_name"], account)
		if account["parent_account"] and accounts_dict[account["parent_account"]]:
			accounts_dict[account["parent_account"]]["is_group"] = 1

	message = validate_root(accounts_dict)
	if message: return message
	message = validate_account_types(accounts_dict)
	if message: return message

	return [True, len(accounts)]

def validate_root(accounts):
	roots = [accounts[d] for d in accounts if not accounts[d].get('parent_account')]
	if len(roots) < 4:
		return _("Number of root accounts cannot be less than 4")

	for account in roots:
		if not account.get("root_type"):
			return _("Please enter Root Type for - {0}").format(account.get("account_name"))
		elif account.get("root_type") not in ("Asset", "Liability", "Expense", "Income", "Equity"):
			return _('Root Type for "{0}" must be one of the Asset, Liability, Income, Expense and Equity').format(account.get("account_name"))

def validate_account_types(accounts):
	account_types_for_ledger = ["Cost of Goods Sold", "Depreciation", "Fixed Asset", "Payable", "Receivable", "Stock Adjustment"]
	account_types = [accounts[d]["account_type"] for d in accounts if not accounts[d]['is_group']]

	missing = list(set(account_types_for_ledger) - set(account_types))
	if missing:
		return _("Please identify/create Account (Ledger) for type - {0}").format(' , '.join(missing))

	account_types_for_group = ["Bank", "Cash", "Stock"]
	account_groups = [accounts[d]["account_type"] for d in accounts if accounts[d]['is_group']]

	missing = list(set(account_types_for_group) - set(account_groups))
	if missing:
		return _("Please identify/create Account (Group) for type - {0}").format(' , '.join(missing))

def unset_existing_data(company):
	linked = frappe.db.sql('''select fieldname from tabDocField
		where fieldtype="Link" and options="Account" and parent="Company"''', as_dict=True)

	# remove accounts data from company
	update_values = {d.fieldname: '' for d in linked}
	frappe.db.set_value('Company', company, update_values, update_values)

	# remove accounts data from various doctypes
	for doctype in ["Account", "Party Account", "Mode of Payment Account", "Tax Withholding Account",
		"Sales Taxes and Charges Template", "Purchase Taxes and Charges Template"]:
		frappe.db.sql('''delete from `tab{0}` where `company`="%s"''' # nosec
			.format(doctype) % (company))

def set_default_accounts(company):
	from erpnext.setup.doctype.company.company import install_country_fixtures
	company = frappe.get_doc('Company', company)
	company.update({
		"default_receivable_account": frappe.db.get_value("Account",
			{"company": company.name, "account_type": "Receivable", "is_group": 0}),
		"default_payable_account": frappe.db.get_value("Account",
			{"company": company.name, "account_type": "Payable", "is_group": 0})
	})

	company.save()
	install_country_fixtures(company.name)
	company.create_default_tax_template()
