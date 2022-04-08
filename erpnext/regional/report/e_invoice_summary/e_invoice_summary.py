# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def validate_filters(filters=None):
	if filters is None:
		filters = {}
	filters = frappe._dict(filters)

	if not filters.company:
		frappe.throw(
			_("{} is mandatory for generating E-Invoice Summary Report").format(_("Company")),
			title=_("Invalid Filter"),
		)
	if filters.company:
		# validate if company has e-invoicing enabled
		pass
	if not filters.from_date or not filters.to_date:
		frappe.throw(
			_("From Date & To Date is mandatory for generating E-Invoice Summary Report"),
			title=_("Invalid Filter"),
		)
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"), title=_("Invalid Filter"))


def get_data(filters=None):
	if filters is None:
		filters = {}
	query_filters = {
		"posting_date": ["between", [filters.from_date, filters.to_date]],
		"einvoice_status": ["is", "set"],
		"company": filters.company,
	}
	if filters.customer:
		query_filters["customer"] = filters.customer
	if filters.status:
		query_filters["einvoice_status"] = filters.status

	data = frappe.get_all(
		"Sales Invoice", filters=query_filters, fields=[d.get("fieldname") for d in get_columns()]
	)

	return data


def get_columns():
	return [
		{"fieldtype": "Date", "fieldname": "posting_date", "label": _("Posting Date"), "width": 0},
		{
			"fieldtype": "Link",
			"fieldname": "name",
			"label": _("Sales Invoice"),
			"options": "Sales Invoice",
			"width": 140,
		},
		{"fieldtype": "Data", "fieldname": "einvoice_status", "label": _("Status"), "width": 100},
		{"fieldtype": "Link", "fieldname": "customer", "options": "Customer", "label": _("Customer")},
		{"fieldtype": "Check", "fieldname": "is_return", "label": _("Is Return"), "width": 85},
		{"fieldtype": "Data", "fieldname": "ack_no", "label": "Ack. No.", "width": 145},
		{"fieldtype": "Data", "fieldname": "ack_date", "label": "Ack. Date", "width": 165},
		{"fieldtype": "Data", "fieldname": "irn", "label": _("IRN No."), "width": 250},
		{
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"fieldname": "base_grand_total",
			"label": _("Grand Total"),
			"width": 120,
		},
	]
