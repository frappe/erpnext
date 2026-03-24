import frappe


def execute():
	values = frappe.db.get_singles_dict("Accounts Settings")

	frozen_till = values.get("acc_frozen_upto")
	modifier = values.get("frozen_accounts_modifier")

	if not frozen_till and not modifier:
		return

	for company in frappe.get_all("Company", pluck="name"):
		frappe.db.set_value(
			"Company",
			company,
			{
				"accounts_frozen_till_date": frozen_till,
				"role_allowed_for_frozen_entries": modifier,
			},
		)
