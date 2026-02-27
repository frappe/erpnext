import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	copy_doctypes()
	rename_fields()


def copy_doctypes():
	insert_into_bom()
	insert_into_job_card()
	insert_into_subcontracting_inward()


def insert_into_bom():
	fields = ["parent", "idx", "item_code", "item_name", "stock_uom", "stock_qty"]
	data = frappe.get_all("BOM Scrap Item", {"docstatus": 1}, fields)
	if data:
		values = [
			(*item.values(), 1, "secondary_items", item.stock_uom, 1, item.stock_qty, 1) for item in data
		]
		frappe.db.bulk_insert(
			"BOM Secondary Item",
			fields=[*fields, "docstatus", "parentfield", "uom", "conversion_factor", "qty", "is_legacy"],
			values=values,
		)


def insert_into_job_card():
	fields = ["item_code", "item_name", "description", "stock_qty", "stock_uom"]
	bulk_insert("Job Card Scrap Item", "Job Card Secondary Item", fields, ["type"], ["Scrap"])


def insert_into_subcontracting_inward():
	fields = [
		"item_code",
		"fg_item_code",
		"stock_uom",
		"warehouse",
		"reference_name",
		"produced_qty",
		"delivered_qty",
	]
	bulk_insert(
		"Subcontracting Inward Order Scrap Item",
		"Subcontracting Inward Order Secondary Item",
		fields,
		["type"],
		["Scrap"],
	)


def bulk_insert(old_doctype, new_doctype, old_fields, new_fields, new_values):
	data = frappe.get_all(old_doctype, {"docstatus": 1}, ["parent", "idx", *old_fields])
	if data:
		values = [(1, "secondary_items", *item.values(), *new_values) for item in data]
		frappe.db.bulk_insert(
			new_doctype, fields=["docstatus", "parentfield", *old_fields, *new_fields], values=values
		)


def rename_fields():
	rename_field("BOM", "scrap_material_cost", "secondary_items_cost")
	rename_field("BOM", "base_scrap_material_cost", "base_secondary_items_cost")
	rename_field("Stock Entry Detail", "is_scrap_item", "is_legacy_scrap_item")
	rename_field(
		"Manufacturing Settings",
		"set_op_cost_and_scrap_from_sub_assemblies",
		"set_op_cost_and_secondary_items_from_sub_assemblies",
	)
	rename_field("Selling Settings", "deliver_scrap_items", "deliver_secondary_items")
	rename_field("Subcontracting Receipt Item", "is_scrap_item", "is_legacy_scrap_item")
	rename_field("Subcontracting Receipt Item", "scrap_cost_per_qty", "secondary_items_cost_per_qty")
