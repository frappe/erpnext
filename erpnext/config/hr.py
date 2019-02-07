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
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Employee Attendance Tool",
					"hide_count": True,
					"onboard": 1,
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Attendance",
					"onboard": 1,
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Attendance Request",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Upload Attendance",
					"hide_count": True,
					"dependencies": ["Employee"]
				},
			]
		},
		{
			"label": _("Payroll"),
			"items": [
				{
					"type": "doctype",
					"name": "Salary Structure",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Salary Structure Assignment",
					"onboard": 1,
					"dependencies": ["Salary Structure", "Employee"],
				},
				{
					"type": "doctype",
					"name": "Salary Slip",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Payroll Entry",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Employee Benefit Application",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Benefit Claim",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Additional Salary",
				},
				{
					"type": "doctype",
					"name": "Employee Tax Exemption Declaration",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Tax Exemption Proof Submission",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Incentive",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Retention Bonus",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Payroll Period",
				},
				{
					"type": "doctype",
					"name": "Salary Component",
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
			"label": _("Leaves"),
			"items": [
				{
					"type": "doctype",
					"name": "Leave Application",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Leave Allocation",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Compensatory Leave Request",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Leave Encashment",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Leave Period",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name":"Leave Type",
				},
				{
					"type": "doctype",
					"name": "Leave Policy",
					"dependencies": ["Leave Type"]
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
			"label": _("Recruitment and Training"),
			"items": [
				{
					"type": "doctype",
					"name": "Job Applicant",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Job Opening",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Job Offer",
					"onboard": 1,
				},
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
			"label": _("Employee Lifecycle"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Transfer",
					"dependencies": ["Employee"],
				},
				{
					"type": "doctype",
					"name": "Employee Promotion",
					"dependencies": ["Employee"],
				},
				{
					"type": "doctype",
					"name": "Employee Separation",
					"dependencies": ["Employee"],
				},
				{
					"type": "doctype",
					"name": "Employee Onboarding",
					"dependencies": ["Job Applicant"],
				},
				{
					"type": "doctype",
					"name": "Employee Separation Template",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Onboarding Template",
					"dependencies": ["Employee"]
				}
			]
		},
		{
			"label": _("Appraisals, Expense Claims and Loans"),
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
				{
					"type": "doctype",
					"name": "Employee Advance",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Loan Type",
				},
				{
					"type": "doctype",
					"name": "Loan Application",
					"dependencies": ["Employee"]
				},
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
				{
					"type": "report",
					"is_query_report": True,
					"name": "Department Analytics",
					"doctype": "Employee"
				},
			]
		},
		{
			"label": _("Shifts and Fleet Management"),
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
				},
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
		# {
		# 	"label": _("Help"),
		# 	"icon": "fa fa-facetime-video",
		# 	"items": [
		# 		{
		# 			"type": "help",
		# 			"label": _("Setting up Employees"),
		# 			"youtube_id": "USfIUdZlUhw"
		# 		},
		# 		{
		# 			"type": "help",
		# 			"label": _("Leave Management"),
		# 			"youtube_id": "fc0p_AXebc8"
		# 		},
		# 		{
		# 			"type": "help",
		# 			"label": _("Expense Claims"),
		# 			"youtube_id": "5SZHJF--ZFY"
		# 		}
		# 	]
		# },
	]
