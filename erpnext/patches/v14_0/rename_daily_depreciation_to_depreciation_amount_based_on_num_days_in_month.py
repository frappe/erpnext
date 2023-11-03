# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.utils.rename_field import rename_field


def execute():
	try:
		rename_field(
			"Asset Finance Book", "daily_depreciation", "depreciation_amount_based_on_num_days_in_month"
		)

	except Exception as e:
		if e.args[0] != 1054:
			raise
