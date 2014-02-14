// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

frappe.module_page["HR"] = [
	{
		title: frappe._("Top"),
		top: true,
		icon: "icon-copy",
		items: [
			{
				label: frappe._("Employee"),
				description: frappe._("Employee records."),
				doctype:"Employee"
			},
			{
				label: frappe._("Leave Application"),
				description: frappe._("Applications for leave."),
				doctype:"Leave Application"
			},
			{
				label: frappe._("Expense Claim"),
				description: frappe._("Claims for company expense."),
				doctype:"Expense Claim"
			},
			{
				label: frappe._("Salary Slip"),
				description: frappe._("Monthly salary statement."),
				doctype:"Salary Slip"
			},
			{
				label: frappe._("Attendance"),
				description: frappe._("Attendance record."),
				doctype:"Attendance"
			},
		]
	},
	{
		title: frappe._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: frappe._("Job Applicant"),
				description: frappe._("Applicant for a Job."),
				doctype:"Job Applicant"
			},
			{
				label: frappe._("Appraisal"),
				description: frappe._("Performance appraisal."),
				doctype:"Appraisal"
			},
		]
	},
	{
		title: frappe._("Leave Setup"),
		icon: "icon-cog",
		items: [
			{
				"route":"Form/Upload Attendance/Upload Attendance",
				"label":frappe._("Upload Attendance"),
				"description":frappe._("Upload attendance from a .csv file"),
				doctype: "Upload Attendance"
			},
			{
				"route":"Form/Leave Control Panel/Leave Control Panel",
				"label": frappe._("Leave Allocation Tool"),
				"description": frappe._("Allocate leaves for the year."),
				doctype: "Leave Control Panel"
			},
			{
				"label":frappe._("Leave Allocation"),
				"description":frappe._("Leave allocations."),
				doctype: "Leave Allocation"
			},
			{
				"label":frappe._("Leave Type"),
				"description":frappe._("Type of leaves like casual, sick etc."),
				doctype: "Leave Type"
			},
			{
				"label":frappe._("Holiday List"),
				"description":frappe._("List of holidays."),
				doctype: "Holiday List"
			},
			{
				"label":frappe._("Leave Block List"),
				"description":frappe._("Block leave applications by department."),
				doctype: "Leave Block List"
			},
		]
	},
	{
		title: frappe._("Payroll Setup"),
		icon: "icon-cog",
		items: [
			{
				"label": frappe._("Salary Structure"),
				"description": frappe._("Monthly salary template."),
				doctype: "Salary Structure"
			},
			{
				"route":"Form/Salary Manager/Salary Manager",
				"label":frappe._("Process Payroll"),
				"description":frappe._("Generate Salary Slips"),
				doctype: "Salary Manager"
			},
			{
				"label": frappe._("Earning Type"),
				"description": frappe._("Salary components."),
				doctype: "Earning Type"
			},
			{
				"label": frappe._("Deduction Type"),
				"description": frappe._("Tax and other salary deductions."),
				doctype: "Deduction Type"
			},
		]
	},
	{
		title: frappe._("Employee Setup"),
		icon: "icon-cog",
		items: [
			{
				label: frappe._("Job Opening"),
				description: frappe._("Opening for a Job."),
				doctype:"Job Opening"
			},
			{
				"label": frappe._("Employment Type"),
				"description": frappe._("Type of employment master."),
				doctype: "Employment Type"
			},	
			{
				"label": frappe._("Designation"),
				"description": frappe._("Employee Designation."),
				doctype: "Designation"
			},	
			{
				"label": frappe._("Appraisal Template"),
				"description": frappe._("Template for employee performance appraisals."),
				doctype: "Appraisal Template"
			},
			{
				"label": frappe._("Expense Claim Type"),
				"description": frappe._("Types of Expense Claim."),
				doctype: "Expense Claim Type"
			},
			{
				"label": frappe._("Branch"),
				"description": frappe._("Company branches."),
				doctype: "Branch"
			},
			{
				"label": frappe._("Department"),
				"description": frappe._("Company departments."),
				doctype: "Department"
			},
			{
				"label": frappe._("Grade"),
				"description": frappe._("Employee grades"),
				doctype: "Grade"
			},
		]
	},
	{
		title: frappe._("Setup"),
		icon: "icon-cog",
		items: [
			{
				"label": frappe._("HR Settings"),
				"route": "Form/HR Settings",
				"doctype":"HR Settings",
				"description": "Settings for HR Module"
			}
		]
	},
	{
		title: frappe._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":frappe._("Employee Leave Balance"),
				route: "query-report/Employee Leave Balance",
				doctype: "Leave Application"
			},
			{
				"label":frappe._("Employee Birthday"),
				route: "query-report/Employee Birthday",
				doctype: "Employee"
			},
			{
				"label":frappe._("Employee Information"),
				route: "Report/Employee/Employee Information",
				doctype: "Employee"
			},
			{
				"label":frappe._("Monthly Salary Register"),
				route: "query-report/Monthly Salary Register",
				doctype: "Salary Slip"
			},
			{
				"label":frappe._("Monthly Attendance Sheet"),
				route: "query-report/Monthly Attendance Sheet",
				doctype: "Attendance"
			},
		]
	}
];

pscript['onload_hr-home'] = function(wrapper) {
	frappe.views.moduleview.make(wrapper, "HR");
}