import frappe
from frappe import _
from frappe.utils import flt

from erpnext.subcontracting.report.utils import get_inward_order_columns, get_open_inward_order_rows


def execute(filters=None):
	return get_columns(), get_data(filters)


def get_data(filters):
	rows = get_open_inward_order_rows(
		filters,
		"received_items",
		["main_item_code", "rm_item_code", "stock_uom", "required_qty", "received_qty", "returned_qty"],
		[
			["per_produced", "<", 100],
			["Subcontracting Inward Order Received Item", "is_customer_provided_item", "=", 1],
		],
	)

	precision = frappe.get_precision("Subcontracting Inward Order Received Item", "required_qty")
	for row in rows:
		row.pending_qty = flt(row.required_qty - row.received_qty + row.returned_qty, precision)

	return [row for row in rows if row.pending_qty > 0]


def get_columns():
	return [
		*get_inward_order_columns(),
		{
			"label": _("Finished Good"),
			"fieldname": "main_item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": _("Raw Material"),
			"fieldname": "rm_item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": _("Required Qty"), "fieldname": "required_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Received Qty"), "fieldname": "received_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Returned Qty"), "fieldname": "returned_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Pending Qty"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 110},
	]
