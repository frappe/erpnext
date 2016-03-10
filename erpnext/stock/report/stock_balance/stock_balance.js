// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Balance"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": sys_defaults.year_start_date,
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Item",
			"reqd": 1,
			"on_change": function(me) {
				frappe.query_reports["Stock Balance"].toggle_mandatory_filters(me);
			}
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Warehouse",
			"reqd": 1,
			"on_change": function(me) {
				frappe.query_reports["Stock Balance"].toggle_mandatory_filters(me);
			}
		},
	],

	"toggle_mandatory_filters": function(me) {
		var values = me.get_values(false);
		var item_filter = me.filters_by_name["item_code"];
		var warehouse_filter = me.filters_by_name["warehouse"];

		if (values.item_code) {
			warehouse_filter.df.reqd = 0;
		} else if (values.warehouse) {
			item_filter.df.reqd = 0;
		} else {
			item_filter.df.reqd = 1;
			warehouse_filter.df.reqd = 1;
		}

		item_filter.set_mandatory(values.item_code);
		warehouse_filter.set_mandatory(values.warehouse);
	}
}
