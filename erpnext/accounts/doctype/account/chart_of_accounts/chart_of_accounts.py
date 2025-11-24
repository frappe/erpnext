# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import os

import frappe
from frappe.utils import cstr
from frappe.utils.nestedset import rebuild_tree
from unidecode import unidecode


def create_charts(
	company, chart_template=None, existing_company=None, custom_chart=None, from_coa_importer=None
):
	chart = custom_chart or get_chart(chart_template, existing_company)
	if chart:
		accounts = []

		def _import_accounts(children, parent, root_type, root_account=False):
			nonlocal custom_chart
			for account_name, child in children.items():
				if root_account:
					root_type = child.get("root_type")

				if account_name not in get_chart_metadata_fields():
					account_number = cstr(child.get("account_number")).strip()
					account_name, account_name_in_db = add_suffix_if_duplicate(
						account_name, account_number, accounts
					)

					is_group = identify_is_group(child)
					report_type = (
						"Balance Sheet"
						if root_type in ["Asset", "Liability", "Equity"]
						else "Profit and Loss"
					)

					account = frappe.get_doc(
						{
							"doctype": "Account",
							"account_name": child.get("account_name") if from_coa_importer else account_name,
							"company": company,
							"parent_account": parent,
							"is_group": is_group,
							"root_type": root_type,
							"report_type": report_type,
							"account_number": account_number,
							"account_type": child.get("account_type"),
							"account_category": child.get("account_category"),
							"account_currency": child.get("account_currency")
							if custom_chart
							else frappe.get_cached_value("Company", company, "default_currency"),
							"tax_rate": child.get("tax_rate"),
						}
					)

					if root_account or frappe.local.flags.allow_unverified_charts:
						account.flags.ignore_mandatory = True

					account.flags.ignore_permissions = True

					account.insert()

					accounts.append(account_name_in_db)

					_import_accounts(child, account.name, root_type)

		# Rebuild NestedSet HSM tree for Account Doctype
		# after all accounts are already inserted.
		frappe.local.flags.ignore_update_nsm = True
		_import_accounts(chart, None, None, root_account=True)
		rebuild_tree("Account")
		frappe.local.flags.ignore_update_nsm = False


def add_suffix_if_duplicate(account_name, account_number, accounts):
	if account_number:
		account_name_in_db = unidecode(" - ".join([account_number, account_name.strip().lower()]))
	else:
		account_name_in_db = unidecode(account_name.strip().lower())

	if account_name_in_db in accounts:
		count = accounts.count(account_name_in_db)
		account_name = account_name + " " + cstr(count)

	return account_name, account_name_in_db


def identify_is_group(child):
	if child.get("is_group"):
		is_group = child.get("is_group")
	elif len(set(child.keys()) - set(get_chart_metadata_fields())):
		is_group = 1
	else:
		is_group = 0

	return is_group


@frappe.whitelist()
def get_chart(chart_template, existing_company=None):
	chart = {}
	if existing_company:
		return get_account_tree_from_existing_company(existing_company)

	elif chart_template == "Standard":
		from erpnext.accounts.doctype.account.chart_of_accounts.verified import (
			standard_chart_of_accounts,
		)

		return standard_chart_of_accounts.get()
	elif chart_template == "Standard with Numbers":
		from erpnext.accounts.doctype.account.chart_of_accounts.verified import (
			standard_chart_of_accounts_with_account_number,
		)

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
					with open(os.path.join(path, fname)) as f:
						chart = f.read()
						if chart and json.loads(chart).get("name") == chart_template:
							return json.loads(chart).get("tree")


@frappe.whitelist()
def get_charts_for_country(country, with_standard=False):
	charts = []

	def _get_chart_name(content):
		if content:
			content = json.loads(content)
			if (
				content and content.get("disabled", "No") == "No"
			) or frappe.local.flags.allow_unverified_charts:
				charts.append(content["name"])

	country_code = frappe.get_cached_value("Country", country, "code")
	if country_code:
		folders = ("verified",)
		if frappe.local.flags.allow_unverified_charts:
			folders = ("verified", "unverified")

		for folder in folders:
			path = os.path.join(os.path.dirname(__file__), folder)
			if not os.path.exists(path):
				continue

			for fname in os.listdir(path):
				fname = frappe.as_unicode(fname)
				if (fname.startswith(country_code) or fname.startswith(country)) and fname.endswith(".json"):
					with open(os.path.join(path, fname)) as f:
						_get_chart_name(f.read())

	# if more than one charts, returned then add the standard
	if len(charts) != 1 or with_standard:
		charts += ["Standard", "Standard with Numbers"]

	return charts


def get_account_tree_from_existing_company(existing_company):
	all_accounts = frappe.get_all(
		"Account",
		filters={"company": existing_company},
		fields=[
			"name",
			"account_name",
			"parent_account",
			"account_type",
			"is_group",
			"root_type",
			"tax_rate",
			"account_number",
			"account_currency",
		],
		order_by="lft, rgt",
	)

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
		if child.account_number:
			tree[child.account_name]["account_number"] = child.account_number
		if child.account_type:
			tree[child.account_name]["account_type"] = child.account_type
		if child.tax_rate:
			tree[child.account_name]["tax_rate"] = child.tax_rate
		if child.account_currency:
			tree[child.account_name]["account_currency"] = child.account_currency
		if not parent:
			tree[child.account_name]["root_type"] = child.root_type

		# call recursively to build a subtree for current account
		build_account_tree(tree[child.account_name], child, all_accounts)


@frappe.whitelist()
def validate_bank_account(coa, bank_account):
	accounts = []
	chart = get_chart(coa)

	if chart:

		def _get_account_names(account_master):
			for account_name, child in account_master.items():
				if account_name not in get_chart_metadata_fields():
					accounts.append(account_name)

					_get_account_names(child)

		_get_account_names(chart)

	return bank_account in accounts


@frappe.whitelist()
def build_tree_from_json(chart_template, chart_data=None, from_coa_importer=False):
	"""get chart template from its folder and parse the json to be rendered as tree"""
	chart = chart_data or get_chart(chart_template)

	# if no template selected, return as it is
	if not chart:
		return

	accounts = []

	def _import_accounts(children, parent):
		"""recursively called to form a parent-child based list of dict from chart template"""
		for account_name, child in children.items():
			account = {}
			if account_name in get_chart_metadata_fields():
				continue

			if from_coa_importer:
				account_name = child["account_name"]

			account["parent_account"] = parent
			account["expandable"] = True if identify_is_group(child) else False
			account["value"] = (
				(cstr(child.get("account_number")).strip() + " - " + account_name)
				if child.get("account_number")
				else account_name
			)
			accounts.append(account)
			_import_accounts(child, account["value"])

	_import_accounts(chart, None)
	return accounts


def get_chart_metadata_fields():
	return [
		"account_name",
		"account_number",
		"account_type",
		"account_category",
		"root_type",
		"is_group",
		"tax_rate",
		"account_currency",
	]
