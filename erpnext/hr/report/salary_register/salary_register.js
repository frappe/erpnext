// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Salary Register"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"from_date",
			"label": __("From"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.month_start(), -1),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.month_start(), -1),
			"reqd": 1
		},
		{
			"fieldname":"employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname": "docstatus",
			"label": __("Document Status"),
			"fieldtype": "Select",
			"options": ["Draft", "Submitted", "Cancelled", "Draft and Submitted"],
			"default": "Draft and Submitted"
		},
		{
			"fieldname": "group_by_1",
			"label": __("Group By Level 1"),
			"fieldtype": "Select",
			"options": ["Ungrouped", "Group by Department", "Group by Designation", "Group by Branch"],
			"default": "Ungrouped"
		},
		{
			"fieldname": "show_date_of_joining",
			"label": __("Show Date of Joining"),
			"fieldtype": "Check",
		},
		{
			"fieldname": "show_working_days",
			"label": __("Show Working Days"),
			"fieldtype": "Check",
		},
		{
			"fieldname": "show_department",
			"label": __("Show Department"),
			"fieldtype": "Check",
		},
		{
			"fieldname": "show_designation",
			"label": __("Show Designation"),
			"fieldtype": "Check",
		},
		{
			"fieldname": "show_branch",
			"label": __("Show Branch"),
			"fieldtype": "Check",
		},
	],
	formatter: function(value, row, column, data, default_formatter) {
		var style = {};
		var link;

		if (column.fieldname == "leave_without_pay" && flt(value)) {
			style['color'] = 'red';
		}
		if (column.fieldname == "late_days" && flt(value)) {
			style['color'] = 'orange';
		}

		if (data && ['leave_without_pay', 'late_days'].includes(column.fieldname) && data.employee && data.start_date && data.end_date) {
			link = `/app/query-report/Employee Checkin Sheet?employee=${encodeURIComponent(data.employee)}&from_date=${data.start_date}&to_date=${data.end_date}`
		}

		if (column.is_earning || ['gross_pay', 'net_pay', 'rounded_total'].includes(column.fieldname)) {
			style['color'] = 'green';
		} else if (column.is_deduction || column.fieldname == 'total_deduction') {
			style['color'] = 'red';
		} else if (['loan_repayment', 'advance_deduction'].includes(column.fieldname)) {
			style['color'] = 'orange';
		}

		if (['gross_pay', 'total_deduction', 'rounded_total'].includes(column.fieldname)) {
			style['font-weight'] = 'bold';
		}

		return default_formatter(value, row, column, data, {css: style, link_href: link, link_target: "_blank"});
	},
}
