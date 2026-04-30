import frappe

# Snapshot of the relevant German defaults when this migration was written.
# Migration patches must not read mutable setup data, otherwise future edits to
# country_wise_tax.json would change what this patch does on sites that have not
# run it yet.
NOT_APPLICABLE_7_PERCENT_ACCOUNTS = frozenset(
	{
		"Umsatzsteuer 7 %",
		"Umsatzsteuer aus innergemeinschaftlichem Erwerb",
		"Umsatzsteuer nach § 13b UStG",
		"Abziehbare Vorsteuer 7 %",
		"Abziehbare Vorsteuer aus innergemeinschaftlichem Erwerb",
		"Abziehbare Vorsteuer nach § 13b UStG",
	}
)

NOT_APPLICABLE_19_PERCENT_ACCOUNTS = frozenset(
	{
		"Umsatzsteuer 19 %",
		"Umsatzsteuer aus innergemeinschaftlichem Erwerb 19 %",
		"Umsatzsteuer nach § 13b UStG 19 %",
		"Abziehbare Vorsteuer 19 %",
		"Abziehbare Vorsteuer aus innergemeinschaftlichem Erwerb 19 %",
		"Abziehbare Vorsteuer nach § 13b UStG 19 %",
	}
)

GERMAN_ITEM_TAX_TEMPLATE_NOT_APPLICABLE_ACCOUNTS = {
	chart: {
		"19 %": NOT_APPLICABLE_7_PERCENT_ACCOUNTS,
		"7 %": NOT_APPLICABLE_19_PERCENT_ACCOUNTS,
		"0 %": NOT_APPLICABLE_7_PERCENT_ACCOUNTS
		| NOT_APPLICABLE_19_PERCENT_ACCOUNTS
		| frozenset({"Entstandene Einfuhrumsatzsteuer"}),
	}
	for chart in ("SKR03 mit Kontonummern", "SKR04 mit Kontonummern")
}


def execute():
	"""Backfill `not_applicable` on Item Tax Template Details for German companies.

	Before the `not_applicable` flag existed, German default templates used
	`tax_rate: 0` to mean "this tax does not apply to the item" (as opposed to
	an explicit 0% rate). For each German company, this patch looks up the
	historical defaults for its Chart of Accounts and sets
	`not_applicable = 1` on detail rows that still match those defaults
	(same template title, same zero-rate tax account set, flag still unset),
	leaving any user-customised rows untouched.
	"""
	companies = frappe.get_all(
		"Company",
		filters={"country": "Germany"},
		fields=["name", "chart_of_accounts"],
	)

	for company in companies:
		chart = GERMAN_ITEM_TAX_TEMPLATE_NOT_APPLICABLE_ACCOUNTS.get(company.chart_of_accounts)
		if not chart:
			continue

		for template_title, target_accounts in chart.items():
			itt_names = frappe.get_all(
				"Item Tax Template",
				filters={"company": company.name, "title": template_title},
				pluck="name",
			)
			for itt_name in itt_names:
				zero_rate_details = frappe.get_all(
					"Item Tax Template Detail",
					filters={"parent": itt_name, "tax_rate": 0},
					fields=["name", "tax_type", "not_applicable"],
				)
				zero_rate_accounts_by_detail = {
					d.name: frappe.get_cached_value("Account", d.tax_type, "account_name")
					for d in zero_rate_details
				}
				if set(zero_rate_accounts_by_detail.values()) != target_accounts:
					continue

				for d in zero_rate_details:
					if not d.not_applicable:
						frappe.db.set_value(
							"Item Tax Template Detail",
							d.name,
							"not_applicable",
							1,
							update_modified=False,
						)
