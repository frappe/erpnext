# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Slab"),
			"fieldname": "slab",
			"fieldtype": "Link",
			"options": "Slab",
			"width": 180,
		},
		{
			"label": _("Template"),
			"fieldname": "template",
			"fieldtype": "Link",
			"options": "Item",
			"width": 220,
		},
		{
			"label": _("Batch No"),
			"fieldname": "batch_no",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Serial No"),
			"fieldname": "serial_no",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Slab Grade"),
			"fieldname": "grade",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Production Line"),
			"fieldname": "production_line",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Mixer No"),
			"fieldname": "mixer_no",
			"fieldtype": "Data",
			"width": 150,
		},
	]


def get_data(filters):
	item_code = filters.get("item_code")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	if not item_code or not from_date or not to_date:
		return []

	data = frappe.db.sql(
		"""
        SELECT DISTINCT
            sle.slab AS slab,
            slab.batch_number AS batch_no,
            slab.serial_number AS serial_no,
			slab.grade as grade,
            slab.line AS production_line,
			slab.child_line as mixer_no,
            slab.template AS template
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabSlab` slab ON slab.name = sle.slab
        WHERE sle.item_code = %(item_code)s
          AND sle.actual_qty > 0
          AND sle.warehouse LIKE %(warehouse)s
          AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND sle.slab IS NOT NULL
          AND sle.slab != ''
        ORDER BY sle.slab
    """,
		{
			"item_code": item_code,
			"from_date": from_date,
			"to_date": to_date,
			"warehouse": "%%Finished Goods Warehouse%%",
		},
		as_dict=True,
	)

	return data
