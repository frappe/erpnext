// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Salary Assignment Report"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => {
				return {
					filters: {
						'status': "Active"
					}
				}
			}
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "payroll_entry",
			label: __("Payroll Entry"),
			fieldtype: "Link",
			options: "Payroll Entry",
			reqd: 1,
			get_query: () => {
				return {
					filters: {
						'docstatus': 1
					}
				}
			}
		},
		{
			fieldname: "salary_component",
			label: __("Salary Component"),
			fieldtype: "Link",
			options: "Salary Component",
			get_query: () => {
				return {
					filters: {
						'docstatus': "Enabled"
					}
				}
			}
		},
	]
};
