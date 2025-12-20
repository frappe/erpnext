import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
	field_exists,
	get_inventory_dimensions,
)


def execute():
	if not frappe.db.has_table("Closing Stock Balance"):
		return

	add_inventory_dimensions_to_stock_closing_balance()
	create_stock_closing_entries()


def add_inventory_dimensions_to_stock_closing_balance():
	inventory_dimensions = get_inventory_dimensions()

	dimension_fields_list = []
	for inv_dim in inventory_dimensions:
		if not frappe.db.get_value(
			"Custom Field", {"dt": "Stock Closing Balance", "fieldname": inv_dim.fieldname}
		) and not field_exists("Stock Closing Balance", inv_dim.fieldname):
			dimension_field = frappe._dict()
			dimension_field["mandatory_depends_on"] = ""
			dimension_field["reqd"] = 0
			dimension_field["fieldname"] = inv_dim.fieldname
			dimension_field["label"] = inv_dim.dimension_name
			dimension_field["fieldtype"] = "Link"
			dimension_field["options"] = inv_dim.doctype
			dimension_field["read_only"] = 1
			dimension_field["insert_after"] = "inventory_dimension_section"
			dimension_field["search_index"] = 1
			dimension_fields_list.append(dimension_field)

	if dimension_fields_list:
		dimension_fields_list.insert(
			0,
			{
				"label": _("Inventory Dimension"),
				"fieldtype": "Section Break",
				"fieldname": "inventory_dimension_section",
				"insert_after": "stock_uom",
			},
		)
		create_custom_fields({"Stock Closing Balance": dimension_fields_list})


def create_stock_closing_entries():
	for row in frappe.get_all(
		"Closing Stock Balance",
		fields=["company", "status", "from_date", "to_date"],
		filters={"docstatus": 1},
		group_by="company",
		order_by="creation desc",
	):
		new_entry = frappe.new_doc("Stock Closing Entry")
		new_entry.update(row)
		new_entry.save(ignore_permissions=True)
		new_entry.submit()
