import frappe, erpnext

def get_filters():
	company = erpnext.get_default_company()

	if not company:
		company = frappe.db.get_value("Company", {"is_group": 0}, "name")

	return\
{
	"Completed Operation": [
		[
			"Work Order Operation",
			"docstatus",
			"=",
			1,
			0
		]
	],
	"Job Card Analysis": {
		"company": company,
		"docstatus": 1,
		"range": "Monthly"
	},
	"Last Month Downtime Analysis": {},
	"Pending Work Order": {
		"charts_based_on": "Age",
		"company": company
	},
	"Produced Quantity": [
		[
			"Work Order",
			"docstatus",
			"=",
			1,
			0
		]
	],
	"Quality Inspection Analysis": {},
	"Work Order Analysis": {
		"charts_based_on": "Status",
		"company": company
	},
	"Work Order Qty Analysis": {
		"charts_based_on": "Quantity",
		"company": company
	}
}