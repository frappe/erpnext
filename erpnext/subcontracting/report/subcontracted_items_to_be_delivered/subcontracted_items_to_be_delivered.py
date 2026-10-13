import frappe
from frappe import _
from frappe.utils import flt

from erpnext.subcontracting.report.utils import get_inward_order_columns, get_open_inward_order_rows


def execute(filters=None):
	return get_columns(), get_data(filters)


def get_data(filters):
	rows = get_open_inward_order_rows(
		filters,
		"items",
		["item_code", "item_name", "stock_uom", "qty", "produced_qty", "delivered_qty"],
		[],
	)

	precision = frappe.get_precision("Subcontracting Inward Order Item", "qty")
	for row in rows:
		row.pending_qty = flt(row.qty - row.delivered_qty, precision)

	return [row for row in rows if row.pending_qty > 0]


def get_columns():
	return [
		*get_inward_order_columns(),
		{
			"label": _("Finished Good"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
		{"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": _("Order Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 110},
		{"label": _("Produced Qty"), "fieldname": "produced_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Delivered Qty"), "fieldname": "delivered_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Pending Qty"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 110},
	]
