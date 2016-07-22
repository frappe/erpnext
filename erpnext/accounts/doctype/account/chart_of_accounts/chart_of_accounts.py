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
			for account_name, child in children.items():
				if root_account:
					root_type = child.get("root_type")

				if account_name not in ["account_type", "root_type", "is_group"]:

					account_name_in_db = unidecode(account_name.strip().lower())
					if account_name_in_db in accounts:
						count = accounts.count(account_name_in_db)
						account_name = account_name + " " + cstr(count)

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

def identify_is_group(child):
	if child.get("is_group"):
		is_group = child.get("is_group")
	elif len(set(child.keys()) - set(["account_type", "root_type", "is_group"])):
		is_group = 1
	else:
		is_group = 0

	return is_group

def get_chart(chart_name):
	chart = {}
	if chart_name == "Standard":
		from erpnext.accounts.doctype.account.chart_of_accounts.verified import standard_chart_of_accounts
		return standard_chart_of_accounts.get()
	else:
		folders = ("verified",)
		if frappe.local.flags.allow_unverified_charts:
			folders = ("verified", "unverified")
		for folder in folders:
			path = os.path.join(os.path.dirname(__file__), folder)
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
				if fname.startswith(country_code) and fname.endswith(".json"):
					with open(os.path.join(path, fname), "r") as f:
						_get_chart_name(f.read())

	if len(charts) != 1:
		charts.append("Standard")

	return charts
