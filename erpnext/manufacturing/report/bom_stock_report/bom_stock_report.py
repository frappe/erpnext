# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint
from frappe import _
from erpnext.stock.doctype.item.item import convert_item_uom_for


def execute(filters=None):
	filters = frappe._dict(filters)
	filters.show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

	data = get_bom_stock(filters)
	columns = get_columns(filters)

	return columns, data


def get_bom_stock(filters):
	qty_to_produce = flt(filters.get("qty_to_produce", 1)) or 1
	if flt(qty_to_produce) <= 0:
		frappe.throw(_("Quantity to Produce can not be less than Zero"))

	bom_item_table = "tabBOM Item"
	if filters.get("show_exploded_view"):
		bom_item_table = "tabBOM Explosion Item"

	conditions = get_conditions(filters)

	data = frappe.db.sql("""
		SELECT bom_item.item_code, bom_item.item_name,
			bom_item.qty as bom_qty,
			bom_item.qty * {qty_to_produce} / bom.quantity as required_qty,
			bom_item.uom, bin.stock_uom, bom.uom as production_uom,
			sum(bin.actual_qty) as actual_qty,
			bom.quantity as bom_unit_qty
		FROM `tabBOM` bom
		INNER JOIN `{bom_item_table}` bom_item ON bom_item.parent = bom.name and bom_item.parenttype = 'BOM'
		LEFT JOIN `tabBin` bin ON bom_item.item_code = bin.item_code
		WHERE {conditions}
		GROUP BY bom_item.item_code
		ORDER BY bom_item.idx
	""".format(bom_item_table=bom_item_table, conditions=conditions, qty_to_produce=qty_to_produce), filters, as_dict=1)

	for d in data:
		d.actual_qty = convert_item_uom_for(d.actual_qty, d.item_code, d.stock_uom, d.uom)
		d.producible_qty = (d.actual_qty / (d.bom_qty / d.bom_unit_qty))
		d.disable_item_formatter = cint(filters.show_item_name)

	return data


def get_conditions(filters):
	conditions = []

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions.append("""exists (select name from `tabWarehouse` wh
				where wh.lft >= {0} and wh.rgt <= {1} and bin.warehouse = wh.name)
			""".format(warehouse_details.lft, warehouse_details.rgt))
		else:
			conditions.append("bin.warehouse = {0}".format(frappe.db.escape(filters.get("warehouse"))))

	if filters.get("bom"):
		conditions.append("bom.name = %(bom)s")

	return " and ".join(conditions)


def get_columns(filters):
	columns = [
		{"label": _("Item Code"), "fieldtype": "Link", "fieldname": "item_code", "options": "Item",
			"width": 120 if filters.show_item_name else 200},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
		{"label": _("UOM"), "fieldtype": "Link", "options": "UOM", "fieldname": "uom", "width": 50},
		{"label": _("BOM Qty"), "fieldname": "bom_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Required Qty"), "fieldname": "required_qty", "fieldtype": "Float", "width": 100},
		{"label": _("In Stock"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Enough To Produce"), "fieldname": "producible_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Production UOM"), "fieldname": "production_uom", "fieldtype": "Link", "options": "UOM", "width": 80},
	]

	if not filters.show_item_name:
		columns = [c for c in columns if c.get('fieldname') != 'item_name']

	return columns
