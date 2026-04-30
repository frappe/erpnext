import frappe

# Snapshot of the relevant German defaults when this migration was written.
# Migration patches must not read mutable setup data, otherwise future edits to
# country_wise_tax.json would change what this patch does on sites that have not
# run it yet.
#
# For numbered charts, compare account_number + root_type because Account.account_name
# is not unique within a company.
SKR04_NOT_APPLICABLE_7_PERCENT_ACCOUNT_IDS = frozenset(
	{
		("3801", "Liability"),
		("3802", "Liability"),
		("3835", "Liability"),
		("1401", "Asset"),
		("1402", "Asset"),
		("1541", "Asset"),
	}
)

SKR04_NOT_APPLICABLE_19_PERCENT_ACCOUNT_IDS = frozenset(
	{
		("3806", "Liability"),
		("3804", "Liability"),
		("3837", "Liability"),
		("1406", "Asset"),
		("1404", "Asset"),
		("1540", "Asset"),
	}
)

SKR03_NOT_APPLICABLE_7_PERCENT_ACCOUNT_IDS = frozenset(
	{
		("1771", "Liability"),
		("1772", "Liability"),
		("1785", "Liability"),
		("1571", "Asset"),
		("1572", "Asset"),
		("1541", "Asset"),
	}
)

SKR03_NOT_APPLICABLE_19_PERCENT_ACCOUNT_IDS = frozenset(
	{
		("1776", "Liability"),
		("1774", "Liability"),
		("1787", "Liability"),
		("1576", "Asset"),
		("1574", "Asset"),
		("1540", "Asset"),
	}
)

STANDARD_NOT_APPLICABLE_7_PERCENT_ACCOUNT_LABELS = frozenset(
	{
		("Umsatzsteuer 7 %", "Liability"),
		("Umsatzsteuer aus innergemeinschaftlichem Erwerb", "Liability"),
		("Umsatzsteuer nach § 13b UStG", "Liability"),
		("Abziehbare Vorsteuer 7 %", "Asset"),
		("Abziehbare Vorsteuer aus innergemeinschaftlichem Erwerb", "Asset"),
		("Abziehbare Vorsteuer nach § 13b UStG", "Asset"),
	}
)

STANDARD_NOT_APPLICABLE_19_PERCENT_ACCOUNT_LABELS = frozenset(
	{
		("Umsatzsteuer 19 %", "Liability"),
		("Umsatzsteuer aus innergemeinschaftlichem Erwerb 19 %", "Liability"),
		("Umsatzsteuer nach § 13b UStG 19 %", "Liability"),
		("Abziehbare Vorsteuer 19 %", "Asset"),
		("Abziehbare Vorsteuer aus innergemeinschaftlichem Erwerb 19 %", "Asset"),
		("Abziehbare Vorsteuer nach § 13b UStG 19 %", "Asset"),
	}
)

STANDARD_WITH_NUMBERS_NOT_APPLICABLE_7_PERCENT_ACCOUNT_IDS = frozenset(
	{
		("2321", "Liability"),
		("2331", "Liability"),
		("2341", "Liability"),
		("1521", "Asset"),
		("1531", "Asset"),
		("1541", "Asset"),
	}
)

STANDARD_WITH_NUMBERS_NOT_APPLICABLE_19_PERCENT_ACCOUNT_IDS = frozenset(
	{
		("2320", "Liability"),
		("2330", "Liability"),
		("2340", "Liability"),
		("1520", "Asset"),
		("1530", "Asset"),
		("1540", "Asset"),
	}
)

GERMAN_ITEM_TAX_TEMPLATE_NOT_APPLICABLE_ACCOUNTS = {
	"SKR03 mit Kontonummern": {
		"identifier_field": "account_number",
		"templates": {
			"19 %": SKR03_NOT_APPLICABLE_7_PERCENT_ACCOUNT_IDS,
			"7 %": SKR03_NOT_APPLICABLE_19_PERCENT_ACCOUNT_IDS,
			"0 %": SKR03_NOT_APPLICABLE_7_PERCENT_ACCOUNT_IDS
			| SKR03_NOT_APPLICABLE_19_PERCENT_ACCOUNT_IDS
			| frozenset({("1588", "Asset")}),
		},
	},
	"SKR04 mit Kontonummern": {
		"identifier_field": "account_number",
		"templates": {
			"19 %": SKR04_NOT_APPLICABLE_7_PERCENT_ACCOUNT_IDS,
			"7 %": SKR04_NOT_APPLICABLE_19_PERCENT_ACCOUNT_IDS,
			"0 %": SKR04_NOT_APPLICABLE_7_PERCENT_ACCOUNT_IDS
			| SKR04_NOT_APPLICABLE_19_PERCENT_ACCOUNT_IDS
			| frozenset({("1433", "Asset")}),
		},
	},
	"Standard": {
		"identifier_field": "account_name",
		"templates": {
			"19 %": STANDARD_NOT_APPLICABLE_7_PERCENT_ACCOUNT_LABELS,
			"7 %": STANDARD_NOT_APPLICABLE_19_PERCENT_ACCOUNT_LABELS,
			"0%": STANDARD_NOT_APPLICABLE_7_PERCENT_ACCOUNT_LABELS
			| STANDARD_NOT_APPLICABLE_19_PERCENT_ACCOUNT_LABELS
			| frozenset({("Entstandene Einfuhrumsatzsteuer", "Asset")}),
		},
	},
	"Standard with Numbers": {
		"identifier_field": "account_number",
		"templates": {
			"19%": STANDARD_WITH_NUMBERS_NOT_APPLICABLE_7_PERCENT_ACCOUNT_IDS,
			"7%": STANDARD_WITH_NUMBERS_NOT_APPLICABLE_19_PERCENT_ACCOUNT_IDS,
			"0 %": STANDARD_WITH_NUMBERS_NOT_APPLICABLE_7_PERCENT_ACCOUNT_IDS
			| STANDARD_WITH_NUMBERS_NOT_APPLICABLE_19_PERCENT_ACCOUNT_IDS
			| frozenset({("1550", "Asset")}),
		},
	},
}


def update_account_cache(accounts, account_cache):
	missing_accounts = set(accounts) - set(account_cache)
	if not missing_accounts:
		return

	for account in frappe.get_all(
		"Account",
		filters={"name": ("in", tuple(sorted(missing_accounts)))},
		fields=["name", "account_name", "account_number", "root_type"],
	):
		account_cache[account.name] = account


def get_account_identifier(account, identifier_field, account_cache):
	cached_account = account_cache.get(account)
	if not cached_account:
		return None

	return cached_account.get(identifier_field), cached_account.root_type


def execute():
	"""Backfill `not_applicable` on Item Tax Template Details for German companies.

	Before the `not_applicable` flag existed, German default templates used
	`tax_rate: 0` to mean "this tax does not apply to the item" (as opposed to
	an explicit 0% rate). For each German company, this patch looks up the
	historical defaults for its Chart of Accounts and sets
	`not_applicable = 1` on detail rows that still match those defaults
	(same template title, same zero-rate tax account identifier set, flag still unset),
	leaving any user-customised rows untouched.
	"""
	companies = frappe.get_all(
		"Company",
		filters={"country": "Germany"},
		fields=["name", "chart_of_accounts"],
	)
	account_cache = {}

	for company in companies:
		chart = GERMAN_ITEM_TAX_TEMPLATE_NOT_APPLICABLE_ACCOUNTS.get(company.chart_of_accounts)
		if not chart:
			continue

		identifier_field = chart["identifier_field"]
		for template_title, target_accounts in chart["templates"].items():
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
				update_account_cache((d.tax_type for d in zero_rate_details), account_cache)
				zero_rate_accounts_by_detail = {
					d.name: get_account_identifier(d.tax_type, identifier_field, account_cache)
					for d in zero_rate_details
				}
				if any(identifier is None for identifier in zero_rate_accounts_by_detail.values()):
					continue

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
