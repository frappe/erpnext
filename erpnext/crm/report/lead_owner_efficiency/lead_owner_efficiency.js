// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
<<<<<<< HEAD
	frappe.query_reports["Lead Owner Efficiency"] = {
		"filters": [
			{
				"fieldname": "from_date",
				"label": __("From Date"),
				"fieldtype": "Date",
				"default": frappe.defaults.get_user_default("year_start_date"),
			},
			{
				"fieldname": "to_date",
				"label": __("To Date"),
				"fieldtype": "Date",
				"default": frappe.defaults.get_user_default("year_end_date"),
			}
		]};
=======
frappe.query_reports["Lead Owner Efficiency"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
		},
	],
};
>>>>>>> ec74a5e566 (style: format js files)
