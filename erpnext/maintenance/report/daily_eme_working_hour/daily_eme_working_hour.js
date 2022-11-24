// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Daily EME Working Hour"] = {
	"filters": [
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"on_change" : function(query_report) {
				var branch = query_report.get_filter_value('branch');
				if ( !branch ){
					return;
				}
				frappe.call({
					method: 'frappe.client.get_value',
					args: {
						doctype: 'Branch',
						filters: { 
							'name': branch
						},
						fieldname: ['cost_center'],
					},
					callback: function(r){
						if (r.message.cost_center){
							query_report.set_filter_value('cost_center', r.message.cost_center)
							query_report.refresh();
						}else{
							query_report.set_filter_value('cost_center', "")
						}
					}
				})	
			}
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Data",
			"read_only": 1
		},
		{
			"fieldname": "supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier"
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start()
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default":frappe.datetime.get_today()
		},
		{
			"fieldname" : "equipment_type",
			"label": __("Equipment Type"),
			"fieldtype": "Link",
			"options": "Equipment Type"
		},
		{
			"fieldname": "company_owned",
			"label": __("Company Owned"),
			"fieldtype": "Check"
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && column.id == "equipment_type" ) {
			value = "<span style='color:black!important; font-weight:bold'; font-style: italic !important;'>" + value + "</span>";
		}
		return value;
	},
}

