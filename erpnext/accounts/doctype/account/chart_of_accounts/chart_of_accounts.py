# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, os, json
from frappe.utils import cstr
from unidecode import unidecode

def create_charts(chart_name, company):
	chart = get_chart(chart_name)

	if chart:
		accounts = []

		def _import_accounts(children, parent, root_type, root_account=False):
			for account_name, children in children.items():
				if root_account:
					root_type = children.get("root_type")

				if account_name not in ["account_type", "root_type", "group_or_ledger"]:

					account_name_in_db = unidecode(account_name.strip().lower())
					if account_name_in_db in accounts:
						count = accounts.count(account_name_in_db)
						account_name = account_name + " " + cstr(count)

					group_or_ledger = identify_group_or_ledger(children)
					report_type = "Balance Sheet" if root_type in ["Asset", "Liability", "Equity"] \
						else "Profit and Loss"

					account = frappe.get_doc({
						"doctype": "Account",
						"account_name": account_name,
						"company": company,
						"parent_account": parent,
						"group_or_ledger": group_or_ledger,
						"root_type": root_type,
						"report_type": report_type,
						"account_type": children.get("account_type")
					})

					if root_account:
						account.flags.ignore_mandatory = True

					account.insert()

					accounts.append(account_name_in_db)

					_import_accounts(children, account.name, root_type)

		_import_accounts(chart, None, None, root_account=True)

def identify_group_or_ledger(children):
	if children.get("group_or_ledger"):
		group_or_ledger = children.get("group_or_ledger")
	elif len(set(children.keys()) - set(["account_type", "root_type", "group_or_ledger"])):
		group_or_ledger = "Group"
	else:
		group_or_ledger = "Ledger"

	return group_or_ledger

def get_chart(chart_name):
	chart = {}
	if chart_name == "Standard":
		from erpnext.accounts.doctype.account.chart_of_accounts.verified import standard_chart_of_accounts
		return standard_chart_of_accounts.coa
	else:
		path = os.path.join(os.path.dirname(__file__), "verified")
		for fname in os.listdir(path):
			if fname.endswith(".json"):
				with open(os.path.join(path, fname), "r") as f:
					chart = f.read()
					if chart and json.loads(chart).get("name") == chart_name:
						return json.loads(chart).get("tree")

@frappe.whitelist()
def get_charts_for_country(country):
	charts = []

	def _get_chart_name(content):
		if content:
			content = json.loads(content)
			if content and content.get("is_active", "No") == "Yes" and content.get("disabled", "No") == "No":
				charts.append(content["name"])

	country_code = frappe.db.get_value("Country", country, "code")
	path = os.path.join(os.path.dirname(__file__), "verified")
	for fname in os.listdir(path):
		if fname.startswith(country_code) and fname.endswith(".json"):
			with open(os.path.join(path, fname), "r") as f:
				_get_chart_name(f.read())

	countries_use_OHADA_system = ["Benin", "Burkina Faso", "Cameroon", "Central African Republic", "Comoros",
		"Congo", "Ivory Coast", "Gabon", "Guinea", "Guinea Bissau", "Equatorial Guinea", "Mali", "Niger",
		"Replica of Democratic Congo", "Senegal", "Chad", "Togo"]

	if country in countries_use_OHADA_system:
		with open(os.path.join(os.path.dirname(__file__), "syscohada_syscohada_chart_template.json"), "r") as f:
			_get_chart_name(f.read())

	if len(charts) != 1:
		charts.append("Standard")

	return charts
