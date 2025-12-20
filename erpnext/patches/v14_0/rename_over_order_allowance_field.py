from frappe.model.utils.rename_field import rename_field


def execute():
	rename_field(
		"Buying Settings",
		"over_order_allowance",
		"blanket_order_allowance",
	)

	rename_field(
		"Selling Settings",
		"over_order_allowance",
		"blanket_order_allowance",
	)
