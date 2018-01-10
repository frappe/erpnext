// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Profit and Loss Statement"] = $.extend({},
		erpnext.financial_statements);

	frappe.query_reports["Profit and Loss Statement"]["filters"].push(
		{
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center"
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		}
		,
		{
			"fieldname": "accumulated_values",
			"label": __("Accumulated Values"),
			"fieldtype": "Check"
		}
		,
		{
			"fieldname": "included_cost_centers",
			"label": __("Included Cost Centers"),
			"fieldtype": "Data"
		}
		//~ ,
		//~ {
			//~ "fieldname": "from_date",
			//~ "label": __("From Date"),
			//~ "fieldtype": "Date"
		//~ }
		//~ ,
		//~ {
			//~ "fieldname": "to_date",
			//~ "label": __("To Date"),
			//~ "fieldtype": "Date"
		//~ }
	);
});
