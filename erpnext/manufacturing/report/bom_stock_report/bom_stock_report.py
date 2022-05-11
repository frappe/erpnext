# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()

	data = get_bom_stock(filters)

	return columns, data


def get_columns():
	"""return columns"""
	columns = [
		_("Item") + ":Link/Item:150",
		_("Description") + "::300",
		_("BOM Qty") + ":Float:160",
		_("BOM UoM") + "::160",
		_("Required Qty") + ":Float:120",
		_("In Stock Qty") + ":Float:120",
		_("Enough Parts to Build") + ":Float:200",
	]

	return columns


def get_bom_stock(filters):
	conditions = ""
	bom = filters.get("bom")

	table = "`tabBOM Item`"
	qty_field = "stock_qty"

	qty_to_produce = filters.get("qty_to_produce", 1)
	if int(qty_to_produce) <= 0:
		frappe.throw(_("Quantity to Produce can not be less than Zero"))

	if filters.get("show_exploded_view"):
		table = "`tabBOM Explosion Item`"

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value(
			"Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1
		)
		if warehouse_details:
			conditions += (
				" and exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and ledger.warehouse = wh.name)"
				% (warehouse_details.lft, warehouse_details.rgt)
			)
		else:
			conditions += " and ledger.warehouse = %s" % frappe.db.escape(filters.get("warehouse"))

	else:
		conditions += ""

	return frappe.db.sql(
		"""
			SELECT
				bom_item.item_code,
				bom_item.description ,
				bom_item.{qty_field},
				bom_item.stock_uom,
				bom_item.{qty_field} * {qty_to_produce} / bom.quantity,
				sum(ledger.actual_qty) as actual_qty,
				sum(FLOOR(ledger.actual_qty / (bom_item.{qty_field} * {qty_to_produce} / bom.quantity)))
			FROM
				`tabBOM` AS bom INNER JOIN {table} AS bom_item
					ON bom.name = bom_item.parent
				LEFT JOIN `tabBin` AS ledger
					ON bom_item.item_code = ledger.item_code
				{conditions}
			WHERE
				bom_item.parent = {bom} and bom_item.parenttype='BOM'

			GROUP BY bom_item.item_code""".format(
			qty_field=qty_field,
			table=table,
			conditions=conditions,
			bom=frappe.db.escape(bom),
			qty_to_produce=qty_to_produce or 1,
		)
	)
