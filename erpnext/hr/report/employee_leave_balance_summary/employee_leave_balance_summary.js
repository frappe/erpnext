// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Employee Leave Balance Summary'] = {
	filters: [
		{
			fieldname:'date',
			label: __('Date'),
			fieldtype: 'Date',
			reqd: 1,
			default: frappe.datetime.now_date()
		},
		{
			fieldname:'company',
			label: __('Company'),
			fieldtype: 'Link',
			options: 'Company',
			reqd: 1,
			default: frappe.defaults.get_user_default('Company')
		},
		{
			fieldname:'employee',
			label: __('Employee'),
			fieldtype: 'Link',
			options: 'Employee',
		},
		{
			fieldname:'department',
			label: __('Department'),
			fieldtype: 'Link',
			options: 'Department',
		},
		{
			fieldname: "employee_status",
			label: __("Employee Status"),
			fieldtype: "Select",
			options: [
				"",
				{ "value": "Active", "label": __("Active") },
				{ "value": "Inactive", "label": __("Inactive") },
				{ "value": "Suspended", "label": __("Suspended") },
				{ "value": "Left", "label": __("Left") },
			],
			default: "Active",
		}
	]
};
