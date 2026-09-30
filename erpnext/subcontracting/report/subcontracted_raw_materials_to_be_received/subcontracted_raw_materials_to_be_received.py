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
		[
			"reference_name",
			"main_item_code",
			"rm_item_code",
			"stock_uom",
			"required_qty",
			"received_qty",
			"returned_qty",
		],
		[
			["per_produced", "<", 100],
			["Subcontracting Inward Order Received Item", "is_customer_provided_item", "=", 1],
		],
	)
	set_pending_qty(rows)

	return [row for row in rows if row.pending_qty > 0]


def set_pending_qty(rows):
	finished_goods = get_finished_goods({row.reference_name for row in rows})
	precision = frappe.get_precision("Subcontracting Inward Order Received Item", "required_qty")
	for row in rows:
		finished_good = finished_goods[row.reference_name]
		row.process_loss_qty = flt(
			row.required_qty / finished_good.qty * finished_good.process_loss_qty, precision
		)
		row.pending_qty = flt(
			row.required_qty - row.received_qty + row.returned_qty + row.process_loss_qty, precision
		)


def get_finished_goods(order_items):
	if not order_items:
		return {}

	return {
		row.name: row
		for row in frappe.get_all(
			"Subcontracting Inward Order Item",
			filters={"name": ["in", list(order_items)]},
			fields=["name", "qty", "process_loss_qty"],
		)
	}


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
		{
			"label": _("Process Loss Qty"),
			"fieldname": "process_loss_qty",
			"fieldtype": "Float",
			"width": 130,
		},
		{"label": _("Pending Qty"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 110},
	]
