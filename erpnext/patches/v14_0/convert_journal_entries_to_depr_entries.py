# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	if not frappe.db.table_exists("Asset") or not frappe.db.table_exists(
		"Asset Depreciation Schedule"
	):
		return

	if not frappe.db.count("Asset") or not frappe.db.count("Asset Depreciation Schedule"):
		return

	if not frappe.db.count("Journal Entry", {"voucher_type": "Depreciation Entry"}):
		return

	jes = get_journal_entries_of_type_depreciation_entry()

	for je in jes:
		journal_entry = frappe.get_doc("Journal Entry", je)

		depr_entry = create_depr_entry(journal_entry)
		replace_je_with_depr_entry(journal_entry, depr_entry)


def get_journal_entries_of_type_depreciation_entry():
	return frappe.get_all(
		"Journal Entry", filters={"voucher_type": "Depreciation Entry"}, pluck="name"
	)


def create_depr_entry(journal_entry):
	depr_entry = frappe.new_doc("Depreciation Entry")
	depr_entry.posting_date = journal_entry.posting_date
	depr_entry.company = journal_entry.company
	depr_entry.asset = journal_entry.accounts[0].reference_name
	depr_entry.finance_book = journal_entry.finance_book
	(
		depr_entry.credit_account,
		depr_entry.debit_account,
		depr_entry.depreciation_amount,
	) = get_depr_details(journal_entry.accounts)
	depr_entry.cost_center = journal_entry.accounts[0].cost_center
	depr_entry.reference_doctype = journal_entry.accounts[0].reference_type
	depr_entry.reference_docname = journal_entry.accounts[0].reference_name
	depr_entry.submit()

	return depr_entry


def get_depr_details(accounts):
	if accounts[0].credit:
		return accounts[0].account, accounts[1].account, accounts[0].credit
	else:
		return accounts[1].account, accounts[0].account, accounts[0].debit


def replace_je_with_depr_entry(journal_entry, depr_entry):
	depr_schedule = frappe.get_value(
		"Asset Depreciation Schedule", {"journal_entry": journal_entry.name}
	)

	frappe.reload_doctype("Asset Depreciation Schedule")

	frappe.db.set_value(
		"Asset Depreciation Schedule", depr_schedule.name, "depreciation_entry", depr_entry.name
	)
