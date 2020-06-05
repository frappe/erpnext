import frappe
from frappe.utils import nowdate, add_months

def get_filters():
	start_date = add_months(nowdate(), -1)
	end_date = nowdate()

	return\
{
	"Monthly Completed Work Order": [
		[
			"Work Order",
			"status",
			"=",
			"Completed"
		],
		[
			"Work Order",
			"docstatus",
			"=",
			1
		],
		[
			"Work Order",
			"creation",
			"between",
			[
				start_date,
				end_date
			]
		]
	],
	"Monthly Quality Inspection": [
		[
			"Quality Inspection",
			"docstatus",
			"=",
			1
		],
		[
			"Quality Inspection",
			"creation",
			"between",
			[
				start_date,
				end_date
			]
		]
	],
	"Monthly Total Work Order": [
		[
			"Work Order",
			"docstatus",
			"=",
			1
		],
		[
			"Work Order",
			"creation",
			"between",
			[
				start_date,
				end_date
			]
		]
	],
	"Ongoing Job Card": [
		[
			"Job Card",
			"status",
			"!=",
			"Completed"
		],
		[
			"Job Card",
			"docstatus",
			"=",
			1
		]
	]
}