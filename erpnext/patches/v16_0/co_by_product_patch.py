from collections import defaultdict

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	copy_doctypes()
	rename_fields()


def copy_doctypes():
	previous = frappe.db.auto_commit_on_many_writes
	frappe.db.auto_commit_on_many_writes = True
	try:
		insert_into_bom()
		insert_into_job_card()
		if frappe.db.has_table("Subcontracting Inward Order Scrap Item"):
			insert_into_subcontracting_inward()
	finally:
		frappe.db.auto_commit_on_many_writes = previous


def insert_into_bom():
	fields = ["item_code", "item_name", "stock_uom", "stock_qty", "rate"]
	data = frappe.get_all("BOM Scrap Item", {"docstatus": ("<", 2)}, ["parent", *fields])
	grouped_data = defaultdict(list)
	for item in data:
		grouped_data[item.parent].append(item)

	for parent, items in grouped_data.items():
		bom = frappe.get_doc("BOM", parent)
		for item in items:
			secondary_item = frappe.new_doc(
				"BOM Secondary Item", parent_doc=bom, parentfield="secondary_items"
			)
			secondary_item.update({field: item[field] for field in fields})
			secondary_item.update(
				{
					"uom": item.stock_uom,
					"conversion_factor": 1,
					"qty": item.stock_qty,
					"is_legacy": 1,
					"type": "Scrap",
				}
			)
			secondary_item.insert()


def insert_into_job_card():
	fields = ["item_code", "item_name", "description", "stock_qty", "stock_uom"]
	bulk_insert("Job Card", "Job Card Scrap Item", "Job Card Secondary Item", fields, ["type"], ["Scrap"])


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
		"Subcontracting Inward Order",
		"Subcontracting Inward Order Scrap Item",
		"Subcontracting Inward Order Secondary Item",
		fields,
		["type"],
		["Scrap"],
	)


def bulk_insert(parent_doctype, old_doctype, new_doctype, old_fields, new_fields, new_values):
	data = frappe.get_all(old_doctype, {"docstatus": ("<", 2)}, ["parent", *old_fields])
	grouped_data = defaultdict(list)

	for item in data:
		grouped_data[item.parent].append(item)

	for parent, items in grouped_data.items():
		parent_doc = frappe.get_doc(parent_doctype, parent)
		for item in items:
			secondary_item = frappe.new_doc(new_doctype, parent_doc=parent_doc, parentfield="secondary_items")
			secondary_item.update({old_field: item[old_field] for old_field in old_fields})
			secondary_item.update(
				{new_field: new_value for new_field, new_value in zip(new_fields, new_values, strict=True)}
			)
			secondary_item.insert()


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
