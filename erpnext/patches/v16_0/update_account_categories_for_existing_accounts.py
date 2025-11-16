# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import get_chart_metadata_fields
from erpnext.accounts.doctype.account.chart_of_accounts.verified import standard_chart_of_accounts
from erpnext.accounts.doctype.financial_report_template.financial_report_template import (
	sync_financial_report_templates,
)


def execute():
	"""
	Patch to create default account categories and update existing accounts
	with appropriate account categories based on standard chart of accounts mapping
	"""
	sync_financial_report_templates()
	update_account_categories()


def update_account_categories():
	account_mapping = get_standard_account_category_mapping()
	companies = frappe.get_all("Company", pluck="name")

	mapped_account_categories = {}

	for company in companies:
		map_account_categories_for_company(company, account_mapping, mapped_account_categories)

	if not mapped_account_categories:
		return

	frappe.db.bulk_update("Account", mapped_account_categories)


def get_standard_account_category_mapping():
	account_mapping = {}

	def _extract_account_mapping(chart_data, prefix=""):
		for account_name, account_details in chart_data.items():
			if account_name in get_chart_metadata_fields():
				continue

			if isinstance(account_details, dict) and account_details.get("account_category"):
				account_mapping[account_name] = account_details["account_category"]

			if isinstance(account_details, dict):
				_extract_account_mapping(account_details, prefix)

	standard_chart = standard_chart_of_accounts.get()
	_extract_account_mapping(standard_chart)

	return account_mapping


def map_account_categories_for_company(company, account_mapping, mapped_account_categories):
	accounts = frappe.get_all(
		"Account",
		filters={"company": company, "account_category": ["is", "not set"]},
		fields=["name", "account_name"],
	)

	for account in accounts:
		account_category = account_mapping.get(account.account_name)

		if account_category:
			mapped_account_categories[account.name] = {"account_category": account_category}
