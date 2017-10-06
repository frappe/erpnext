// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Daily Movements"] = {
	"filters": [
        {
			"fieldname":"start_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"end_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"mode_of_payment",
			"label": __("Medio de Pago"),
			"fieldtype": "Link",
			"options": "Mode of Payment"
		}
	],
	"formatter": function (row, cell, value, columnDef, dataContext, default_formatter) {
	     console.log(row);
	     value = default_formatter(row, cell, value, columnDef, dataContext);
	     if (columnDef.id == __("Concept") && dataContext[__("Concept")] == "Total" ) {
	        value = "<span style='color:red!important;font-weight:bold'>" + value + "</span>";
	     }
	     if (columnDef.id == __("Concept") && dataContext[__("Concept")] == "Balance Inicial" ) {
	        value = "<span style='color:green!important;font-weight:bold'>" + value + "</span>";
	     }
	     return value;
	}

}
