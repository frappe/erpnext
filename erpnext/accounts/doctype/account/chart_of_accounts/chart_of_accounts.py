# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, os, json
from frappe.utils import cstr
from unidecode import unidecode

def create_charts(chart_name, company):
	# ***************
	frappe.db.sql("delete from tabAccount where company=%s", company)
	# ***************

	chart = get_chart(chart_name)

	if chart:
		accounts = []

		def _import_accounts(children, parent, root_type, root_account=False):
			for account_name, children in children.items():
				if root_account:
					root_type = children.get("root_type")

				if account_name not in ["account_type", "root_type"]:

					account_name_in_db = unidecode(account_name.strip().lower())
					if account_name_in_db in accounts:
						count = accounts.count(account_name_in_db)
						account_name = account_name + " " + cstr(count)

					account = frappe.get_doc({
						"doctype": "Account",
						"account_name": account_name,
						"company": company,
						"parent_account": parent,
						"group_or_ledger": "Group" if len(children) else "Ledger",
						"root_type": root_type,
						"report_type": "Balance Sheet" \
							if root_type in ["Asset", "Liability", "Equity"] else "Profit and Loss",
						"account_type": children.get("account_type")
					})

					if root_account:
						account.ignore_mandatory = True

					account.insert()

					accounts.append(account_name_in_db)

					_import_accounts(children, account.name, root_type)

		_import_accounts(chart.get("tree"), None, None, root_account=True)

def get_chart(chart_name):
	chart = {}
	for fname in os.listdir(os.path.dirname(__file__)):
		if fname.endswith(".json"):
			with open(os.path.join(os.path.dirname(__file__), fname), "r") as f:
				chart = json.loads(f.read())
				if chart.get("name") == chart_name:
					return chart

@frappe.whitelist()
def get_charts_for_country(country):
	charts = []
	country_code = frappe.db.get_value("Country", country, "code")

	for fname in os.listdir(os.path.dirname(__file__)):
		if fname.startswith(country_code) and fname.endswith(".json"):
			with open(os.path.join(os.path.dirname(__file__), fname), "r") as f:
				charts.append(json.loads(f.read())["name"])

	countries_use_OHADA_system = ["Benin", "Burkina Faso", "Cameroon", "Central African Republic", "Comoros",
		"Congo", "Ivory Coast", "Gabon", "Guinea", "Guinea Bissau", "Equatorial Guinea", "Mali", "Niger",
		"Replica of Democratic Congo", "Senegal", "Chad", "Togo"]

	if country in countries_use_OHADA_system:
		with open(os.path.join(os.path.dirname(__file__), "syscohada_syscohada_chart_template.json"), "r") as f:
			charts.append(json.loads(f.read())["name"])

	return charts
