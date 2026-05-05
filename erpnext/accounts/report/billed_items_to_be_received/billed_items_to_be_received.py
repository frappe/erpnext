# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _

from erpnext.accounts.report.utils import add_party_name_column, show_party_name


def execute(filters=None):
	data = get_data(filters) or []
	columns = get_columns()

	return columns, data


def get_data(report_filters):
	pi = frappe.qb.DocType("Purchase Invoice")
	pii = frappe.qb.DocType("Purchase Invoice Item")
	query = (
		frappe.qb.from_(pi)
		.inner_join(pii)
		.on(pii.parent == pi.name)
		.select(
			pi.name,
			pi.supplier,
			pi.company,
			pi.posting_date,
			pi.currency,
			pii.item_code,
			pii.item_name,
			pii.uom,
			pii.qty,
			pii.received_qty,
			pii.rate,
			pii.amount,
		)
		.where(
			(pi.company == report_filters.get("company"))
			& (pi.posting_date <= report_filters.get("posting_date"))
			& (pi.docstatus == 1)
			& (pi.per_received < 100)
			& (pi.update_stock == 0)
			& (pi.is_opening != "Yes")
		)
	)

	if report_filters.get("purchase_invoice"):
		query = query.where(pi.name == report_filters.get("purchase_invoice"))

	if show_party_name("Supplier"):
		supplier = frappe.qb.DocType("Supplier")
		query = (
			query.left_join(supplier)
			.on(supplier.name == pi.supplier)
			.select(supplier.supplier_name.as_("supplier_name"))
		)

	return query.run(as_dict=True)


def get_columns():
	columns = [
		{
			"label": _("Purchase Invoice"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Purchase Invoice",
			"width": 170,
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 120,
		},
	]

	add_party_name_column(columns, party_type="Supplier", fieldname="supplier_name")

	columns.extend(
		[
			{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
			{
				"label": _("Item Code"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100,
			},
			{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 100},
			{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 100},
			{"label": _("Invoiced Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
			{"label": _("Received Qty"), "fieldname": "received_qty", "fieldtype": "Float", "width": 100},
			{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 100},
			{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 100},
		]
	)

	return columns
