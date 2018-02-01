# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, os, json
from frappe.utils import cstr
from unidecode import unidecode

def create_charts(company, chart_template=None, existing_company=None):
	chart = get_chart(chart_template, existing_company)
	if chart:
		accounts = []

		def _import_accounts(children, parent, root_type, root_account=False):
			for account_name, child in children.items():
				if root_account:
					root_type = child.get("root_type")

				if account_name not in ["account_number", "account_type",
					"root_type", "is_group", "tax_rate"]:

					account_number = cstr(child.get("account_number")).strip()
					account_name, account_name_in_db = add_suffix_if_duplicate(account_name,
						account_number, accounts)

					is_group = identify_is_group(child)
					report_type = "Balance Sheet" if root_type in ["Asset", "Liability", "Equity"] \
						else "Profit and Loss"

					account = frappe.get_doc({
						"doctype": "Account",
						"account_name": account_name,
						"company": company,
						"parent_account": parent,
						"is_group": is_group,
						"root_type": root_type,
						"report_type": report_type,
						"account_number": account_number,
						"account_type": child.get("account_type"),
						"account_currency": frappe.db.get_value("Company", company, "default_currency"),
						"tax_rate": child.get("tax_rate")
					})

					if root_account or frappe.local.flags.allow_unverified_charts:
						account.flags.ignore_mandatory = True
						
					account.flags.ignore_permissions = True
					
					account.insert()

					accounts.append(account_name_in_db)

					_import_accounts(child, account.name, root_type)

		_import_accounts(chart, None, None, root_account=True)

def add_suffix_if_duplicate(account_name, account_number, accounts):
	if account_number:
		account_name_in_db = unidecode(" - ".join([account_number,
			account_name.strip().lower()]))
	else:
		account_name_in_db = unidecode(account_name.strip().lower())

	if account_name_in_db in accounts:
		count = accounts.count(account_name_in_db)
		account_name = account_name + " " + cstr(count)

	return account_name, account_name_in_db

def identify_is_group(child):
	if child.get("is_group"):
		is_group = child.get("is_group")
	elif len(set(child.keys()) - set(["account_type", "root_type", "is_group", "tax_rate", "account_number"])):
		is_group = 1
	else:
		is_group = 0

	return is_group

def get_chart(chart_template, existing_company=None):
	chart = {}
	if existing_company:
		return get_account_tree_from_existing_company(existing_company)
	
	elif chart_template == "Standard":
		from erpnext.accounts.doctype.account.chart_of_accounts.verified import standard_chart_of_accounts
		return standard_chart_of_accounts.get()
	elif chart_template == "Standard with Numbers":
		from erpnext.accounts.doctype.account.chart_of_accounts.verified \
			import standard_chart_of_accounts_with_account_number
		return standard_chart_of_accounts_with_account_number.get()
	else:
		folders = ("verified",)
		if frappe.local.flags.allow_unverified_charts:
			folders = ("verified", "unverified")
		for folder in folders:
			path = os.path.join(os.path.dirname(__file__), folder)
			for fname in os.listdir(path):
				fname = frappe.as_unicode(fname)
				if fname.endswith(".json"):
					with open(os.path.join(path, fname), "r") as f:
						chart = f.read()
						if chart and json.loads(chart).get("name") == chart_template:
							return json.loads(chart).get("tree")

@frappe.whitelist()
def get_charts_for_country(country, with_standard=False):
	charts = []

	def _get_chart_name(content):
		if content:
			content = json.loads(content)
			if (content and content.get("disabled", "No") == "No") \
				or frappe.local.flags.allow_unverified_charts:
					charts.append(content["name"])

	country_code = frappe.db.get_value("Country", country, "code")
	if country_code:
		folders = ("verified",)
		if frappe.local.flags.allow_unverified_charts:
			folders = ("verified", "unverified")

		for folder in folders:
			path = os.path.join(os.path.dirname(__file__), folder)

			for fname in os.listdir(path):
				fname = frappe.as_unicode(fname)
				if (fname.startswith(country_code) or fname.startswith(country)) and fname.endswith(".json"):
					with open(os.path.join(path, fname), "r") as f:
						_get_chart_name(f.read())

	if len(charts) != 1 or with_standard:
		charts += ["Standard", "Standard with Numbers"]

	return charts


def get_account_tree_from_existing_company(existing_company):
	all_accounts = frappe.get_all('Account',
		filters={'company': existing_company},
		fields = ["name", "account_name", "parent_account", "account_type",
			"is_group", "root_type", "tax_rate", "account_number"],
		order_by="lft, rgt")

	account_tree = {}

	# fill in tree starting with root accounts (those with no parent)
	if all_accounts:
		build_account_tree(account_tree, None, all_accounts)
	return account_tree

def build_account_tree(tree, parent, all_accounts):
	# find children
	parent_account = parent.name if parent else ""
	children = [acc for acc in all_accounts if cstr(acc.parent_account) == parent_account]
			
	# if no children, but a group account
	if not children and parent.is_group:
		tree["is_group"] = 1
		tree["account_number"] = parent.account_number

	# build a subtree for each child
	for child in children:
		# start new subtree
		tree[child.account_name] = {}
		
		# assign account_type and root_type
		if child.account_type:
			tree[child.account_name]["account_number"] = child.account_number
		if child.account_type:
			tree[child.account_name]["account_type"] = child.account_type
		if child.tax_rate:
			tree[child.account_name]["tax_rate"] = child.tax_rate
		if not parent:
			tree[child.account_name]["root_type"] = child.root_type
			
		# call recursively to build a subtree for current account
		build_account_tree(tree[child.account_name], child, all_accounts)