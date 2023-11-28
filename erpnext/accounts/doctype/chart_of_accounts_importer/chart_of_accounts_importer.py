# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import csv
import os
from functools import reduce

import frappe
from frappe import _
from frappe.desk.form.linked_with import get_linked_fields
from frappe.model.document import Document
from frappe.utils import cint, cstr
from frappe.utils.csvutils import UnicodeWriter
from frappe.utils.xlsxutils import (
	read_xls_file_from_attached_file,
	read_xlsx_file_from_attached_file,
)

from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import (
	build_tree_from_json,
	create_charts,
)


class ChartofAccountsImporter(Document):
	def validate(self):
		if self.import_file:
			get_coa(
				"Chart of Accounts Importer", "All Accounts", file_name=self.import_file, for_validate=1
			)


def validate_columns(data):
	if not data:
		frappe.throw(_("No data found. Seems like you uploaded a blank file"))

	no_of_columns = max([len(d) for d in data])

	if no_of_columns > 8:
		frappe.throw(
			_("More columns found than expected. Please compare the uploaded file with standard template"),
			title=(_("Wrong Template")),
		)


@frappe.whitelist()
def validate_company(company):
	parent_company, allow_account_creation_against_child_company = frappe.db.get_value(
		"Company", {"name": company}, ["parent_company", "allow_account_creation_against_child_company"]
	)

	if parent_company and (not allow_account_creation_against_child_company):
		msg = _("{} is a child company.").format(frappe.bold(company)) + " "
		msg += _("Please import accounts against parent company or enable {} in company master.").format(
			frappe.bold(_("Allow Account Creation Against Child Company"))
		)
		frappe.throw(msg, title=_("Wrong Company"))

	if frappe.db.get_all("GL Entry", {"company": company}, "name", limit=1):
		return False


@frappe.whitelist()
def import_coa(file_name, company):
	# delete existing data for accounts
	unset_existing_data(company)

	# create accounts
	file_doc, extension = get_file(file_name)

	if extension == "csv":
		data = generate_data_from_csv(file_doc)
	else:
		data = generate_data_from_excel(file_doc, extension)

	frappe.local.flags.ignore_root_company_validation = True
	forest = build_forest(data)
	create_charts(company, custom_chart=forest, from_coa_importer=True)

	# trigger on_update for company to reset default accounts
	set_default_accounts(company)


def get_file(file_name):
	file_doc = frappe.get_doc("File", {"file_url": file_name})
	parts = file_doc.get_extension()
	extension = parts[1]
	extension = extension.lstrip(".")

	if extension not in ("csv", "xlsx", "xls"):
		frappe.throw(
			_(
				"Only CSV and Excel files can be used to for importing data. Please check the file format you are trying to upload"
			)
		)

	return file_doc, extension


def generate_data_from_csv(file_doc, as_dict=False):
	"""read csv file and return the generated nested tree"""

	file_path = file_doc.get_full_path()

	data = []
	with open(file_path, "r") as in_file:
		csv_reader = list(csv.reader(in_file))
		headers = csv_reader[0]
		del csv_reader[0]  # delete top row and headers row

		for row in csv_reader:
			if as_dict:
				data.append({frappe.scrub(header): row[index] for index, header in enumerate(headers)})
			else:
				if not row[1] and len(row) > 1:
					row[1] = row[0]
					row[3] = row[2]
				data.append(row)

	# convert csv data
	return data


def generate_data_from_excel(file_doc, extension, as_dict=False):
	content = file_doc.get_content()

	if extension == "xlsx":
		rows = read_xlsx_file_from_attached_file(fcontent=content)
	elif extension == "xls":
		rows = read_xls_file_from_attached_file(content)

	data = []
	headers = rows[0]
	del rows[0]

	for row in rows:
		if as_dict:
			data.append({frappe.scrub(header): row[index] for index, header in enumerate(headers)})
		else:
			if not row[1]:
				row[1] = row[0]
				row[3] = row[2]
			data.append(row)

	return data


@frappe.whitelist()
def get_coa(doctype, parent, is_root=False, file_name=None, for_validate=0):
	"""called by tree view (to fetch node's children)"""

	file_doc, extension = get_file(file_name)
	parent = None if parent == _("All Accounts") else parent

	if extension == "csv":
		data = generate_data_from_csv(file_doc)
	else:
		data = generate_data_from_excel(file_doc, extension)

	validate_columns(data)
	validate_accounts(file_doc, extension)

	if not for_validate:
		forest = build_forest(data)
		accounts = build_tree_from_json(
			"", chart_data=forest, from_coa_importer=True
		)  # returns a list of dict in a tree render-able form

		# filter out to show data for the selected node only
		accounts = [d for d in accounts if d["parent_account"] == parent]

		return accounts
	else:
		return {"show_import_button": 1}


def build_forest(data):
	"""
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
	"""

	# set the value of nested dictionary
	def set_nested(d, path, value):
		reduce(lambda d, k: d.setdefault(k, {}), path[:-1], d)[path[-1]] = value
		return d

	# returns the path of any node in list format
	def return_parent(data, child):
		from frappe import _

		for row in data:
			account_name, parent_account, account_number, parent_account_number = row[0:4]
			if account_number:
				account_name = "{} - {}".format(account_number, account_name)
			if parent_account_number:
				parent_account_number = cstr(parent_account_number).strip()
				parent_account = "{} - {}".format(parent_account_number, parent_account)

			if parent_account == account_name == child:
				return [parent_account]
			elif account_name == child:
				parent_account_list = return_parent(data, parent_account)
				if not parent_account_list and parent_account:
					frappe.throw(
						_("The parent account {0} does not exists in the uploaded template").format(
							frappe.bold(parent_account)
						)
					)
				return [child] + parent_account_list

	charts_map, paths = {}, []

	line_no = 2
	error_messages = []

	for i in data:
		(
			account_name,
			parent_account,
			account_number,
			parent_account_number,
			is_group,
			account_type,
			root_type,
			account_currency,
		) = i

		if not account_name:
			error_messages.append("Row {0}: Please enter Account Name".format(line_no))

		name = account_name
		if account_number:
			account_number = cstr(account_number).strip()
			account_name = "{} - {}".format(account_number, account_name)

		charts_map[account_name] = {}
		charts_map[account_name]["account_name"] = name
		if account_number:
			charts_map[account_name]["account_number"] = account_number
		if cint(is_group) == 1:
			charts_map[account_name]["is_group"] = is_group
		if account_type:
			charts_map[account_name]["account_type"] = account_type
		if root_type:
			charts_map[account_name]["root_type"] = root_type
		if account_currency:
			charts_map[account_name]["account_currency"] = account_currency
		path = return_parent(data, account_name)[::-1]
		paths.append(path)  # List of path is created
		line_no += 1

	if error_messages:
		frappe.throw("<br>".join(error_messages))

	out = {}
	for path in paths:
		for n, account_name in enumerate(path):
			set_nested(
				out, path[: n + 1], charts_map[account_name]
			)  # setting the value of nested dictionary.

	return out


def build_response_as_excel(writer):
	filename = frappe.generate_hash("", 10)
	with open(filename, "wb") as f:
		f.write(cstr(writer.getvalue()).encode("utf-8"))
	f = open(filename)
	reader = csv.reader(f)

	from frappe.utils.xlsxutils import make_xlsx

	xlsx_file = make_xlsx(reader, "Chart of Accounts Importer Template")

	f.close()
	os.remove(filename)

	# write out response as a xlsx type
	frappe.response["filename"] = "coa_importer_template.xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"


@frappe.whitelist()
def download_template(file_type, template_type, company):
	writer = get_template(template_type, company)

	if file_type == "CSV":
		# download csv file
		frappe.response["result"] = cstr(writer.getvalue())
		frappe.response["type"] = "csv"
		frappe.response["doctype"] = "Chart of Accounts Importer"
	else:
		build_response_as_excel(writer)


def get_template(template_type, company):
	fields = [
		"Account Name",
		"Parent Account",
		"Account Number",
		"Parent Account Number",
		"Is Group",
		"Account Type",
		"Root Type",
		"Account Currency",
	]
	writer = UnicodeWriter()
	writer.writerow(fields)

	if template_type == "Blank Template":
		for root_type in get_root_types():
			writer.writerow(["", "", "", "", 1, "", root_type])

		for account in get_mandatory_group_accounts():
			writer.writerow(["", "", "", "", 1, account, "Asset"])

		for account_type in get_mandatory_account_types():
			writer.writerow(
				["", "", "", "", 0, account_type.get("account_type"), account_type.get("root_type")]
			)
	else:
		writer = get_sample_template(writer, company)

	return writer


def get_sample_template(writer, company):
	currency = frappe.db.get_value("Company", company, "default_currency")
	with open(os.path.join(os.path.dirname(__file__), "coa_sample_template.csv"), "r") as f:
		for row in f:
			row = row.strip().split(",") + [currency]
			writer.writerow(row)

	return writer


@frappe.whitelist()
def validate_accounts(file_doc, extension):
	if extension == "csv":
		accounts = generate_data_from_csv(file_doc, as_dict=True)
	else:
		accounts = generate_data_from_excel(file_doc, extension, as_dict=True)

	accounts_dict = {}
	for account in accounts:
		accounts_dict.setdefault(account["account_name"], account)
		if "parent_account" not in account:
			msg = _(
				"Please make sure the file you are using has 'Parent Account' column present in the header."
			)
			msg += "<br><br>"
			msg += _("Alternatively, you can download the template and fill your data in.")
			frappe.throw(msg, title=_("Parent Account Missing"))
		if account["parent_account"] and accounts_dict.get(account["parent_account"]):
			accounts_dict[account["parent_account"]]["is_group"] = 1

	validate_root(accounts_dict)

	return [True, len(accounts)]


def validate_root(accounts):
	roots = [accounts[d] for d in accounts if not accounts[d].get("parent_account")]
	error_messages = []

	for account in roots:
		if not account.get("root_type") and account.get("account_name"):
			error_messages.append(
				_("Please enter Root Type for account- {0}").format(account.get("account_name"))
			)
		elif account.get("root_type") not in get_root_types() and account.get("account_name"):
			error_messages.append(
				_("Root Type for {0} must be one of the Asset, Liability, Income, Expense and Equity").format(
					account.get("account_name")
				)
			)

	validate_missing_roots(roots)

	if error_messages:
		frappe.throw("<br>".join(error_messages))


def validate_missing_roots(roots):
	root_types_added = set(d.get("root_type") for d in roots)

	missing = list(set(get_root_types()) - root_types_added)

	if missing:
		frappe.throw(_("Please add Root Account for - {0}").format(" , ".join(missing)))


def get_root_types():
	return ("Asset", "Liability", "Expense", "Income", "Equity")


def get_report_type(root_type):
	if root_type in ("Asset", "Liability", "Equity"):
		return "Balance Sheet"
	else:
		return "Profit and Loss"


def get_mandatory_group_accounts():
	return ("Bank", "Cash", "Stock")


def get_mandatory_account_types():
	return [
		{"account_type": "Cost of Goods Sold", "root_type": "Expense"},
		{"account_type": "Depreciation", "root_type": "Expense"},
		{"account_type": "Fixed Asset", "root_type": "Asset"},
		{"account_type": "Payable", "root_type": "Liability"},
		{"account_type": "Receivable", "root_type": "Asset"},
		{"account_type": "Stock Adjustment", "root_type": "Expense"},
		{"account_type": "Bank", "root_type": "Asset"},
		{"account_type": "Cash", "root_type": "Asset"},
		{"account_type": "Stock", "root_type": "Asset"},
	]


def unset_existing_data(company):
	# remove accounts data from company

	fieldnames = get_linked_fields("Account").get("Company", {}).get("fieldname", [])
	linked = [{"fieldname": name} for name in fieldnames]
	update_values = {d.get("fieldname"): "" for d in linked}
	frappe.db.set_value("Company", company, update_values, update_values)

	# remove accounts data from various doctypes
	for doctype in [
		"Account",
		"Party Account",
		"Mode of Payment Account",
		"Tax Withholding Account",
		"Sales Taxes and Charges Template",
		"Purchase Taxes and Charges Template",
	]:
		frappe.db.sql(
			'''delete from `tab{0}` where `company`="%s"'''.format(doctype) % (company)  # nosec
		)


def set_default_accounts(company):
	from erpnext.setup.doctype.company.company import install_country_fixtures

	company = frappe.get_doc("Company", company)
	company.update(
		{
			"default_receivable_account": frappe.db.get_value(
				"Account", {"company": company.name, "account_type": "Receivable", "is_group": 0}
			),
			"default_payable_account": frappe.db.get_value(
				"Account", {"company": company.name, "account_type": "Payable", "is_group": 0}
			),
			"default_provisional_account": frappe.db.get_value(
				"Account",
				{"company": company.name, "account_type": "Service Received But Not Billed", "is_group": 0},
			),
		}
	)

	company.save()
	install_country_fixtures(company.name, company.country)
	company.create_default_tax_template()
