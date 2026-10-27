# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import csv
import os
from functools import reduce

import frappe
from frappe import _
from frappe.core.doctype.file.utils import find_file_by_url
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
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		import_file: DF.Attach | None
	# end: auto-generated types

	def validate(self):
		if self.import_file:
			get_coa("Chart of Accounts Importer", "All Accounts", file_name=self.import_file, for_validate=1)


def validate_columns(data):
	if not data:
		frappe.throw(_("No data found. Seems like you uploaded a blank file"))

	if any(len(row) != 8 for row in data):
		frappe.throw(
			_(
				"Columns are not according to template. Please compare the uploaded file with standard template"
			),
			title=(_("Wrong Template")),
		)


@frappe.whitelist()
def validate_company(company):
	frappe.has_permission("Chart of Accounts Importer", throw=True)

	parent_company, allow_account_creation_against_child_company = frappe.get_cached_value(
		"Company", company, ["parent_company", "allow_account_creation_against_child_company"]
	)

	if parent_company and (not allow_account_creation_against_child_company):
		msg = _("{} is a child company.").format(frappe.bold(company)) + " "
		msg += _("Please import accounts against parent company or enable {} in company master.").format(
			frappe.bold(_("Allow Account Creation Against Child Company"))
		)
		frappe.throw(msg, title=_("Wrong Company"))

	if frappe.db.get_all("GL Entry", {"company": company}, "name", limit=1):
		frappe.throw(
			_(
				"Transactions against the Company already exist! Chart of Accounts can only be imported for a Company with no transactions."
			)
		)

	validate_user_perms(company)


@frappe.whitelist()
def import_coa(file_name, company):
	frappe.only_for("Accounts Manager")

	# delete existing data for accounts
	frappe.has_permission("Company", "write", company, throw=True)

	# create accounts
	file_doc, extension = get_file(file_name)
	validate_accounts(file_doc, extension)

	if extension == "csv":
		data = generate_data_from_csv(file_doc)
	else:
		data = generate_data_from_excel(file_doc, extension)

	validate_columns(data)
	forest = build_forest(data)

	validate_company(company)

	unset_existing_data(company)

	frappe.local.flags.ignore_root_company_validation = True
	create_charts(company, custom_chart=forest, from_coa_importer=True)

	# trigger on_update for company to reset default accounts
	set_default_accounts(company)


def get_file(file_name):
	file_doc = find_file_by_url(file_name)
	if not file_doc:
		raise frappe.PermissionError

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

	with open(file_doc.get_full_path()) as in_file:
		return generate_data_from_rows(list(csv.reader(in_file)), as_dict)


def generate_data_from_excel(file_doc, extension, as_dict=False):
	content = file_doc.get_content()

	if extension == "xlsx":
		rows = read_xlsx_file_from_attached_file(fcontent=content)
	elif extension == "xls":
		rows = read_xls_file_from_attached_file(content)

	return generate_data_from_rows(rows, as_dict)


def generate_data_from_rows(rows, as_dict=False):
	rows = [row for row in rows if any(cstr(value).strip() for value in row)]
	validate_columns(rows[1:])
	validate_columns(rows[:1])

	headers = rows[0]
	data = []
	for row in rows[1:]:
		if as_dict:
			data.append({frappe.scrub(cstr(header)): row[index] for index, header in enumerate(headers)})
		else:
			if not row[1]:
				row[1] = row[0]
				row[3] = row[2]
			data.append(row)

	return data


@frappe.whitelist()
def get_coa(doctype, parent, is_root=False, file_name=None, for_validate=0):
	"""called by tree view (to fetch node's children)"""

	frappe.has_permission("Chart of Accounts Importer", throw=True)

	file_doc, extension = get_file(file_name)
	parent = None if parent == _("All Accounts") else parent

	if extension == "csv":
		data = generate_data_from_csv(file_doc)
	else:
		data = generate_data_from_excel(file_doc, extension)

	validate_columns(data)
	validate_accounts(file_doc, extension)
	forest = build_forest(data)

	if not for_validate:
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
	validate_columns(data)

	# set the value of nested dictionary
	def set_nested(d, path, value):
		reduce(lambda d, k: d.setdefault(k, {}), path[:-1], d)[path[-1]] = value
		return d

	# returns the path of any node in list format
	def return_parent(parent_accounts, child):
		path = []
		while child:
			if child in path:
				frappe.throw(_("Circular reference found for account {0}").format(frappe.bold(child)))
			path.append(child)
			parent_account = parent_accounts[child]
			if parent_account == child:
				break
			if parent_account and parent_account not in parent_accounts:
				frappe.throw(
					_("The parent account {0} does not exist in the uploaded template").format(
						frappe.bold(parent_account)
					)
				)
			child = parent_account
		return path

	charts_map, parent_accounts = {}, {}

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
			error_messages.append(_("Row {0}: Please enter Account Name").format(line_no))

		name = account_name
		if account_number:
			account_number = cstr(account_number).strip()
			account_name = f"{account_number} - {account_name}"
		if parent_account_number:
			parent_account = f"{cstr(parent_account_number).strip()} - {parent_account}"
		parent_accounts[account_name] = parent_account

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
		line_no += 1

	if error_messages:
		frappe.throw("<br>".join(error_messages))

	out = {}
	for account_name in charts_map:
		path = return_parent(parent_accounts, account_name)[::-1]
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
	frappe.has_permission("Chart of Accounts Importer", throw=True)

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
			writer.writerow(["", "", "", "", 1, "", root_type, ""])

		for account in get_mandatory_group_accounts():
			writer.writerow(["", "", "", "", 1, account, "Asset", ""])

		for account_type in get_mandatory_account_types():
			writer.writerow(
				["", "", "", "", 0, account_type.get("account_type"), account_type.get("root_type"), ""]
			)
	else:
		writer = get_sample_template(writer, company)

	return writer


def get_sample_template(writer, company):
	currency = frappe.db.get_value("Company", company, "default_currency")
	with open(os.path.join(os.path.dirname(__file__), "coa_sample_template.csv")) as f:
		for row in f:
			row = [*row.strip().split(","), currency]
			writer.writerow(row)

	return writer


def validate_accounts(file_doc, extension):
	if extension == "csv":
		accounts = generate_data_from_csv(file_doc, as_dict=True)
	else:
		accounts = generate_data_from_excel(file_doc, extension, as_dict=True)

	accounts_dict = {}
	for account in accounts:
		if not account.get("account_name"):
			frappe.throw(_("Please enter Account Name for every row in the uploaded template"))
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

	account_types = {account.get("account_type") for account in accounts}
	missing = [
		_(account["account_type"])
		for account in get_mandatory_account_types()
		if account["account_type"] not in account_types
	]
	if missing:
		frappe.throw(
			_("Please add accounts for the following Account Types: {0}").format(", ".join(missing)),
			title=_("Missing Account Types"),
		)

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
	frappe.db.set_value("Company", company, dict.fromkeys(fieldnames, ""))

	# import_coa authorizes company replacement; Accounts Manager cannot delete purchase templates.
	for doctype in ("Sales Taxes and Charges Template", "Purchase Taxes and Charges Template"):
		for name in frappe.get_all(doctype, filters={"company": company}, pluck="name"):
			frappe.delete_doc(doctype, name, ignore_permissions=True)

	for doctype in ("Party Account", "Mode of Payment Account", "Tax Withholding Account"):
		frappe.db.delete(doctype, {"company": company})

	# Delete children before their parents, preserving link checks and account validation.
	for name in frappe.get_all("Account", filters={"company": company}, order_by="lft desc", pluck="name"):
		frappe.delete_doc("Account", name)


def validate_user_perms(company):
	# User Permission Check for Account Deletion
	company_accounts_count = frappe.get_query(
		"Account", fields=[{"COUNT": "name"}], filters={"company": company}
	).run()[0][0]
	company_accounts_user_has_access_to = frappe.get_query(
		"Account", fields=[{"COUNT": "name"}], filters={"company": company}, ignore_permissions=False
	).run()[0][0]

	if company_accounts_count != company_accounts_user_has_access_to:
		frappe.throw(
			_("Accounts cannot be removed, as user doesn't have access to all the accounts of {0}").format(
				frappe.bold(company)
			)
		)


def set_default_accounts(company):
	from erpnext.setup.doctype.company.company import install_country_fixtures

	company = frappe.get_doc("Company", company)
	company.update(
		{
			"default_receivable_account": frappe.db.get_value(
				"Account",
				{
					"company": company.name,
					"account_type": "Receivable",
					"is_group": 0,
					"account_currency": company.default_currency,
				},
			),
			"default_payable_account": frappe.db.get_value(
				"Account",
				{
					"company": company.name,
					"account_type": "Payable",
					"is_group": 0,
					"account_currency": company.default_currency,
				},
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
