import frappe


def execute():
	reports = [
		"Accounts Payable",
		"Accounts Payable Summary",
		"Purchase Register",
		"Item-wise Purchase Register",
		"Purchase Order Analysis",
		"Received Items To Be Billed",
		"Supplier Ledger Summary",
	]
	frappe.db.set_value(
		"Workspace Link",
		{
			"parent": "Payables",
			"link_type": "Report",
			"type": "Link",
			"link_to": ["in", reports],
			"is_query_report": 0,
		},
		"is_query_report",
		1,
	)
