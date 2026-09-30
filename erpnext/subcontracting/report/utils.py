import frappe
from frappe import _


def get_inward_order_filters(filters):
	order_filters = [
		["docstatus", "=", 1],
		["company", "=", filters.company],
		["transaction_date", "between", [filters.from_date, filters.to_date]],
	]
	if filters.get("customer"):
		order_filters.append(["customer", "=", filters.customer])

	return order_filters


def get_open_inward_order_rows(filters, table_fieldname, fields, extra_filters):
	return frappe.get_list(
		"Subcontracting Inward Order",
		fields=[
			"name as subcontracting_inward_order",
			"transaction_date",
			"customer",
			*[f"{table_fieldname}.{field}" for field in fields],
		],
		filters=[*get_inward_order_filters(filters), ["status", "!=", "Closed"], *extra_filters],
		order_by=f"transaction_date, name, {table_fieldname}.idx",
	)


def get_inward_order_columns():
	return [
		{
			"label": _("Subcontracting Inward Order"),
			"fieldname": "subcontracting_inward_order",
			"fieldtype": "Link",
			"options": "Subcontracting Inward Order",
			"width": 180,
		},
		{"label": _("Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
	]
