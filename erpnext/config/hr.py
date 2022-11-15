from frappe import _

def get_data():
	return [
		{
			"label": _("Employee"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee",
					"onboard": 1,
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
					"name": "Branch",
				},
				{
					"type": "doctype",
					"name": "Employment Type",
				},

				{
					"type": "doctype",
					"name": "Employee Grade",
				},
				{
					"type": "doctype",
					"name": "Employee Group",
					"dependencies": ["Employee"]
				},
			]
		},
		{
			"label": _("Payroll"),
			"items": [
				{
					"type": "doctype",
					"name": "Payroll Entry",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Salary Slip",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Additional Salary",
				},
				{
					"type": "doctype",
					"name": "Retention Bonus",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Incentive",
					"dependencies": ["Employee"]
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Salary Register",
					"doctype": "Salary Slip"
				},
			]
		},
		{
			"label": _("Attendance"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Monthly Attendance Sheet",
					"doctype": "Attendance",
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employee Checkin Sheet",
					"doctype": "Employee Checkin"
				},
				{
					"type": "doctype",
					"name": "Attendance",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Attendance Request",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Checkin",
					"hide_count": True,
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Upload Attendance",
					"hide_count": True,
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Attendance Tool",
					"hide_count": True,
					"dependencies": ["Employee"]
				},
			]
		},
		{
			"label": _("Leaves"),
			"items": [
				{
					"type": "doctype",
					"name": "Leave Application",
					"onboard": 1,
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
					"type": "report",
					"is_query_report": True,
					"name": "Employee Leave Balance",
					"doctype": "Leave Application"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employee Leave Balance Summary",
					"doctype": "Leave Application"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Leave Ledger Entry",
					"doctype": "Leave Ledger Entry"
				},
			]
		},
		{
			"label": _("Advances and Loans"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Advance",
					"dependencies": ["Employee"],
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Loan",
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Expense Claim",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Loan Application",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Loan Type",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employees Receivable",
					"doctype": "Expense Claim"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employee Ledger Summary",
					"doctype": "Expense Claim"
				},
			]
		},
		{
			"label": _("Shift Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Shift Type",
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Shift Request",
				},
				{
					"type": "doctype",
					"name": "Shift Assignment",
				},
			]
		},
		{
			"label": _("Leave Configuration"),
			"items": [
				{
					"type": "doctype",
					"name": "Leave Policy",
					"onboard": 1,
					"dependencies": ["Leave Type"]
				},
				{
					"type": "doctype",
					"name": "Leave Period",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Leave Type",
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
			"label": _("Payroll Configuration"),
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
					"name": "Payroll Period",
				},
				{
					"type": "doctype",
					"name": "Income Tax Slab",
				},
				{
					"type": "doctype",
					"name": "Salary Component",
				},
			]
		},
		{
			"label": _("Employee Tax"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Opening Income Tax",
					"dependencies": ["Employee"]
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
					"name": "Employee Tax Exemption Category",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Tax Exemption Sub Category",
					"dependencies": ["Employee"]
				},
			]
		},
		{
			"label": _("Employee Benefits"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Other Income",
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
					"name": "Employee Health Insurance"
				},
			]
		},
		{
			"label": _("Employee Lifecycle"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Onboarding",
					"dependencies": ["Job Applicant"],
				},
				{
					"type": "doctype",
					"name": "Employee Promotion",
					"dependencies": ["Employee"],
				},
				{
					"type": "doctype",
					"name": "Employee Transfer",
					"dependencies": ["Employee"],
				},
				{
					"type": "doctype",
					"name": "Employee Separation",
					"dependencies": ["Employee"],
				},
			]
		},
		{
			"label": _("Employee Lifecycle Configuration"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Skill Map",
					"dependencies": ["Employee"],
				},
				{
					"type": "doctype",
					"name": "Employee Onboarding Template",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Separation Template",
					"dependencies": ["Employee"]
				},
			]
		},
		{
			"label": _("Recruitment"),
			"items": [
				{
					"type": "doctype",
					"name": "Job Opening",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Job Applicant",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Job Offer",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Staffing Plan",
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
			"label": _("Performance"),
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
					"type": "doctype",
					"name": "Energy Point Rule",
				},
				{
					"type": "doctype",
					"name": "Energy Point Log",
				},
				{
					"type": "link",
					"doctype": "Energy Point Log",
					"label": _("Energy Point Leaderboard"),
					"route": "#social/users"
				},
			]
		},
		{
			"label": _("Settings"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "HR Settings",
				},
				{
					"type": "doctype",
					"name": "Daily Work Summary Group"
				},
				{
					"type": "page",
					"name": "team-updates",
					"label": _("Team Updates")
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
					"is_query_report": True,
					"name": "Department Analytics",
					"doctype": "Employee"
				},
			]
		},
	]
