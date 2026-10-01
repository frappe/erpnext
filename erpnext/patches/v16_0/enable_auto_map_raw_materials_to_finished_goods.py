import frappe


def execute():
	# keep the order based mapping on submit enabled for existing sites, as on new ones
	frappe.db.set_single_value("Stock Settings", "auto_map_raw_materials_to_finished_goods", 1)
