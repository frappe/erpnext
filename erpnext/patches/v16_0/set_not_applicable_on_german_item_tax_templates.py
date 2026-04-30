import json
from pathlib import Path

import frappe


def execute():
	"""Backfill `not_applicable` on Item Tax Template Details for German companies.

	Before the `not_applicable` flag existed, German default templates used
	`tax_rate: 0` to mean "this tax does not apply to the item" (as opposed to
	an explicit 0% rate). For each German company, this patch looks up the
	defaults for its Chart of Accounts in `country_wise_tax.json` and sets
	`not_applicable = 1` on detail rows that still match those defaults
	(same template title, same tax account, rate still 0, flag still unset),
	leaving any user-customised rows untouched.
	"""
	json_path = (
		Path(frappe.get_app_path("erpnext")) / "setup" / "setup_wizard" / "data" / "country_wise_tax.json"
	)
	germany_charts = json.loads(json_path.read_text()).get("Germany", {}).get("chart_of_accounts", {})
	if not germany_charts:
		return

	companies = frappe.get_all(
		"Company",
		filters={"country": "Germany"},
		fields=["name", "chart_of_accounts"],
	)

	for company in companies:
		chart = germany_charts.get(company.chart_of_accounts) or germany_charts.get("*")
		if not chart:
			continue

		for tmpl in chart.get("item_tax_templates", []):
			target_accounts = {
				tax["tax_type"]["account_name"] for tax in tmpl.get("taxes", []) if tax.get("not_applicable")
			}
			if not target_accounts:
				continue

			itt_names = frappe.get_all(
				"Item Tax Template",
				filters={"company": company.name, "title": tmpl["title"]},
				pluck="name",
			)
			for itt_name in itt_names:
				details = frappe.get_all(
					"Item Tax Template Detail",
					filters={"parent": itt_name, "tax_rate": 0, "not_applicable": 0},
					fields=["name", "tax_type"],
				)
				for d in details:
					account_name = frappe.get_cached_value("Account", d.tax_type, "account_name")
					if account_name in target_accounts:
						frappe.db.set_value(
							"Item Tax Template Detail",
							d.name,
							"not_applicable",
							1,
							update_modified=False,
						)
