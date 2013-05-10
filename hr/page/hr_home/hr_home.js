// ERPNext: Copyright 2013 Web Notes Technologies Pvt Ltd
// GNU General Public License. See "license.txt"

wn.module_page["HR"] = [
	{
		title: wn._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: wn._("Leave Application"),
				description: wn._("Applications for leave."),
				doctype:"Leave Application"
			},
			{
				label: wn._("Expense Claim"),
				description: wn._("Claims for expenses made on behalf of the organization."),
				doctype:"Expense Claim"
			},
			{
				label: wn._("Attendance"),
				description: wn._("Attendance record."),
				doctype:"Attendance"
			},
			{
				label: wn._("Salary Slip"),
				description: wn._("Monthly salary statement."),
				doctype:"Salary Slip"
			},
			{
				label: wn._("Appraisal"),
				description: wn._("Performance appraisal."),
				doctype:"Appraisal"
			},
			{
				label: wn._("Job Applicant"),
				description: wn._("Applicant for a Job (extracted from jobs email)."),
				doctype:"Job Applicant"
			},
		]
	},
	{
		title: wn._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: wn._("Employee"),
				description: wn._("Employee records."),
				doctype:"Employee"
			},
		]
	},
	{
		title: wn._("Leave Setup"),
		icon: "icon-cog",
		items: [
			{
				"route":"Form/Upload Attendance/Upload Attendance",
				"label":wn._("Upload Attendance"),
				"description":wn._("Upload attendance from a .csv file"),
				doctype: "Upload Attendance"
			},
			{
				"route":"Form/Leave Control Panel/Leave Control Panel",
				"label": wn._("Leave Allocation Tool"),
				"description": wn._("Allocate leaves for the year."),
				doctype: "Leave Control Panel"
			},
			{
				"label":wn._("Leave Allocation"),
				"description":wn._("Leave allocations."),
				doctype: "Leave Allocation"
			},
			{
				"label":wn._("Leave Type"),
				"description":wn._("Type of leaves like casual, sick etc."),
				doctype: "Leave Type"
			},
			{
				"label":wn._("Holiday List"),
				"description":wn._("List of holidays."),
				doctype: "Holiday List"
			},
			{
				"label":wn._("Leave Block List"),
				"description":wn._("Block leave applications by department."),
				doctype: "Leave Block List"
			},
		]
	},
	{
		title: wn._("Payroll Setup"),
		icon: "icon-cog",
		items: [
			{
				"label": wn._("Salary Structure"),
				"description": wn._("Monthly salary template."),
				doctype: "Salary Structure"
			},
			{
				"route":"Form/Salary Manager/Salary Manager",
				"label":wn._("Process Payroll"),
				"description":wn._("Generate Salary Slips"),
				doctype: "Salary Manager"
			},
			{
				"label": wn._("Earning Type"),
				"description": wn._("Salary components."),
				doctype: "Earning Type"
			},
			{
				"label": wn._("Deduction Type"),
				"description": wn._("Tax and other salary deductions."),
				doctype: "Deduction Type"
			},
		]
	},
	{
		title: wn._("Employee Setup"),
		icon: "icon-cog",
		items: [
			{
				label: wn._("Job Opening"),
				description: wn._("Opening for a Job."),
				doctype:"Job Opening"
			},
			{
				"label": wn._("Employment Type"),
				"description": wn._("Type of employment master."),
				doctype: "Employment Type"
			},	
			{
				"label": wn._("Designation"),
				"description": wn._("Employee Designation."),
				doctype: "Designation"
			},	
			{
				"label": wn._("Appraisal Template"),
				"description": wn._("Template for employee performance appraisals."),
				doctype: "Appraisal Template"
			},
			{
				"label": wn._("Expense Claim Type"),
				"description": wn._("Types of Expense Claim."),
				doctype: "Expense Claim Type"
			},
			{
				"label": wn._("Branch"),
				"description": wn._("Company branches."),
				doctype: "Branch"
			},
			{
				"label": wn._("Department"),
				"description": wn._("Company departments."),
				doctype: "Department"
			},
			{
				"label": wn._("Grade"),
				"description": wn._("Employee grades"),
				doctype: "Grade"
			},
		]
	},
	{
		title: wn._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":wn._("Employee Leave Balance"),
				route: "query-report/Employee Leave Balance"
			},
			{
				"label":wn._("Employee Birthday"),
				route: "query-report/Employee Birthday"
			},
			{
				"label":wn._("Employee Information"),
				route: "Report2/Employee/Employee Information"
			},
			{
				"label":wn._("Monthly Salary Register"),
				route: "query-report/Monthly Salary Register"
			},
		]
	}
];

pscript['onload_hr-home'] = function(wrapper) {
	wn.views.moduleview.make(wrapper, "HR");
}