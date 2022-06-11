# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	if not frappe.db.count("Asset", {"calculate_depreciation": 1}):
		return

	schedule_rows = frappe.db.sql(
		"""select parent, finance_book, schedule_date, depreciation_amount, accumulated_depreciation_amount, depreciation_entry, finance_book_id, creation
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
			depr_schedule.creation_date = row.creation.date

		depr_schedule.append(
			"depreciation_schedule",
			{
				"schedule_date": row.schedule_date,
				"depreciation_amount": row.depreciation_amount,
				"accumulated_depreciation_amount": row.accumulated_depreciation_amount,
				"depreciation_entry": row.depreciation_entry,
			},
		)
