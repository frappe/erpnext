from frappe.model.utils.rename_field import rename_field


def execute():
	rename_field(
		"Manufacturing Settings",
		"set_op_cost_and_scrape_from_sub_assemblies",
		"set_op_cost_and_scrap_from_sub_assemblies",
	)
