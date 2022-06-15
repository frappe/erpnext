# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	if not frappe.db.count("Asset", {"calculate_depreciation": 1}):
		return

	schedule_rows = frappe.db.sql(
		"""select parent, finance_book, schedule_date, depreciation_amount, accumulated_depreciation_amount, journal_entry, finance_book_id, creation
		from `tabDepreciation Schedule`
		order by parent, finance_book_id
		""",
		as_dict=1,
	)

	parent = ""
	finance_book_id = 0
	depr_schedule = ""

	for row in schedule_rows:
		if parent != row.parent or finance_book_id != row.finance_book_id:
			parent = row.parent
			finance_book_id = row.finance_book_id

			if depr_schedule:
				depr_schedule.submit()

			depr_schedule = frappe.new_doc("Depreciation Schedule")
			depr_schedule.asset = parent
			depr_schedule.finance_book = row.finance_book
			depr_schedule.creation_date = row.creation.date()

		depreciation_entry = None
		if row.journal_entry:
			journal_entry = frappe.get_doc("Journal Entry", row.journal_entry)
			depreciation_entry = create_depr_entry(journal_entry)

			frappe.db.delete("Journal Entry", {"name": journal_entry.name})

		depr_schedule.append(
			"depreciation_schedule",
			{
				"schedule_date": row.schedule_date,
				"depreciation_amount": row.depreciation_amount,
				"accumulated_depreciation_amount": row.accumulated_depreciation_amount,
				"depreciation_entry": depreciation_entry,
			},
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

	return depr_entry.name


def get_depr_details(accounts):
	if accounts[0].credit:
		return accounts[0].account, accounts[1].account, accounts[0].credit
	else:
		return accounts[1].account, accounts[0].account, accounts[0].debit
