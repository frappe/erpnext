// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Balance"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Item Group"
		},
		{
			"fieldname":"brand",
			"label": __("Brand"),
			"fieldtype": "Link",
			"options": "Brand"
		},
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Item",
			"get_query": function() {
				return {
					query: "erpnext.controllers.queries.item_query"
				}
			}
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Warehouse"
		},
		{
			"fieldname":"include_uom",
			"label": __("Include UOM"),
			"fieldtype": "Link",
			"options": "UOM"
		},
		{
			"fieldname": "show_variant_attributes",
			"label": __("Show Variant Attributes"),
			"fieldtype": "Check"
		},
	]
}
