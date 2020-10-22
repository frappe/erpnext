// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.query_reports["Monthly Attendance Sheet"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From date"),
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To date"),
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"fieldname":"employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			get_query: () => {
				var company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						'company': company
					}
				};
			}
		},
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": ["","Branch","Grade","Department","Designation"]
		},
		{
			"fieldname":"summarized_view",
			"label": __("Summarized View"),
			"fieldtype": "Check",
			"Default": 0,
		}
	],
}
