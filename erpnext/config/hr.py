from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Employee and Attendance"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee",
				},
				{
					"type": "doctype",
					"name": "Employee Attendance Tool",
					"hide_count": True
				},
				{
					"type": "doctype",
					"name": "Attendance",
				},
				{
					"type": "doctype",
					"name": "Attendance Request",
				},
				{
					"type": "doctype",
					"name": "Upload Attendance",
					"hide_count": True
				}
			]
		},
		{
			"label": _("Leaves and Holiday"),
			"items": [
				{
					"type": "doctype",
					"name": "Leave Application",
				},
				{
					"type": "doctype",
					"name": "Leave Allocation",
				},
				{
					"type": "doctype",
					"name": "Compensatory Leave Request",
				},
				{
					"type": "doctype",
					"name": "Leave Encashment",
				},
				{
					"type": "doctype",
					"name": "Leave Period",
				},
				{
					"type": "doctype",
					"name": "Leave Policy",
				},
				{
					"type": "doctype",
					"name":"Leave Type",
				},
				{
					"type": "doctype",
					"name": "Holiday List",
				},
				{
					"type": "doctype",
					"name": "Leave Block List",
				},
			]
		},
		{
			"label": _("Payroll"),
			"items": [
				{
					"type": "doctype",
					"name": "Salary Structure Assignment",
				},
				{
					"type": "doctype",
					"name": "Salary Slip",
				},
				{
					"type": "doctype",
					"name": "Payroll Entry"
				},
				{
					"type": "doctype",
					"name": "Employee Benefit Application",
				},
				{
					"type": "doctype",
					"name": "Employee Benefit Claim",
				},
				{
					"type": "doctype",
					"name": "Additional Salary",
				},
				{
					"type": "doctype",
					"name": "Employee Tax Exemption Declaration",
				},
				{
					"type": "doctype",
					"name": "Employee Tax Exemption Proof Submission",
				},
				{
					"type": "doctype",
					"name": "Employee Incentive",
				},
				{
					"type": "doctype",
					"name": "Retention Bonus",
				},
			]
		},
		{
			"label": _("Payroll Setup"),
			"items": [
				{
					"type": "doctype",
					"name": "Payroll Period",
				},
				{
					"type": "doctype",
					"name": "Salary Component",
				},
				{
					"type": "doctype",
					"name": "Salary Structure",
				},
				{
					"type": "doctype",
					"name": "Employee Tax Exemption Category",
				},
				{
					"type": "doctype",
					"name": "Employee Tax Exemption Sub Category"
				}
			]
		},
		{
			"label": _("Travel and Expense Claim"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Advance",
				},
				{
					"type": "doctype",
					"name": "Expense Claim",
				},
				{
					"type": "doctype",
					"name": "Expense Claim Type",
				},
				{
					"type": "doctype",
					"name": "Travel Request",
				},
			]
		},
		{
			"label": _("Appraisals"),
			"items": [
				{
					"type": "doctype",
					"name": "Appraisal",
				},
				{
					"type": "doctype",
					"name": "Appraisal Template",
				},
				{
					"type": "page",
					"name": "team-updates",
					"label": _("Team Updates")
				},
			]
		},
		{
			"label": _("Loan Management"),
			"icon": "icon-list",
			"items": [
				{
					"type": "doctype",
					"name": "Loan Type",
				},
				{
					"type": "doctype",
					"name": "Loan Application",
				},
				{
					"type": "doctype",
					"name": "Loan"
				},
			]
		},
		{
			"label": _("Employee Lifecycle"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Transfer",
				},
				{
					"type": "doctype",
					"name": "Employee Promotion",
				},
				{
					"type": "doctype",
					"name": "Employee Separation",
				},
				{
					"type": "doctype",
					"name": "Employee Onboarding"
				},
				{
					"type": "doctype",
					"name": "Employee Separation Template",
				},
				{
					"type": "doctype",
					"name": "Employee Onboarding Template"
				}
			]
		},
		{
			"label": _("Recruitment"),
			"items": [
				{
					"type": "doctype",
					"name": "Job Applicant",
				},
				{
					"type": "doctype",
					"name": "Job Opening",
				},
				{
					"type": "doctype",
					"name": "Job Offer",
				},
			]
		},
		{
			"label": _("Training"),
			"items": [
				{
					"type": "doctype",
					"name": "Training Program"
				},
				{
					"type": "doctype",
					"name": "Training Event"
				},
				{
					"type": "doctype",
					"name": "Training Result"
				},
				{
					"type": "doctype",
					"name": "Training Feedback"
				},
			]
		},
		{
			"label": _("Shift Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Shift Type",
				},
				{
					"type": "doctype",
					"name": "Shift Request",
				},
				{
					"type": "doctype",
					"name": "Shift Assignment",
				}
			]
		},
		{
			"label": _("Fleet Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle"
				},
				{
					"type": "doctype",
					"name": "Vehicle Log"
				},
			]
		},
		{
			"label": _("Setup"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "HR Settings",
				},
				{
					"type": "doctype",
					"name": "Employment Type",
				},
				{
					"type": "doctype",
					"name": "Branch",
				},
				{
					"type": "doctype",
					"name": "Department",
				},
				{
					"type": "doctype",
					"name": "Designation",
				},
				{
					"type": "doctype",
					"name": "Employee Grade",
				},
				{
					"type": "doctype",
					"name": "Daily Work Summary Group"
				},
				{
					"type": "doctype",
					"name": "Employee Health Insurance"
				},
				{
					"type": "doctype",
					"name": "Staffing Plan",
				}
			]
		},
		{
			"label": _("Reports"),
			"icon": "fa fa-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employee Leave Balance",
					"doctype": "Leave Application"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employee Birthday",
					"doctype": "Employee"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employees working on a holiday",
					"doctype": "Employee"
				},
				{
					"type": "report",
					"name": "Employee Information",
					"doctype": "Employee"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Salary Register",
					"doctype": "Salary Slip"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Monthly Attendance Sheet",
					"doctype": "Attendance"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Expenses",
					"doctype": "Vehicle"
				},

			]
		},
		{
			"label": _("Help"),
			"icon": "fa fa-facetime-video",
			"items": [
				{
					"type": "help",
					"label": _("Setting up Employees"),
					"youtube_id": "USfIUdZlUhw"
				},
				{
					"type": "help",
					"label": _("Leave Management"),
					"youtube_id": "fc0p_AXebc8"
				},
				{
					"type": "help",
					"label": _("Expense Claims"),
					"youtube_id": "5SZHJF--ZFY"
				}
			]
		},
		{
			"label": _("Analytics"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Department Analytics",
					"doctype": "Employee"
				},
			]
		}
	]
