import frappe


def execute():
	# Report sync preserves this setting on older sites.
	frappe.db.set_value(
		"Report",
		{
			"name": [
				"in",
				[
					"Sales Invoice Trends",
					"Purchase Invoice Trends",
					"Sales Order Trends",
					"Quotation Trends",
					"Purchase Order Trends",
					"Delivery Note Trends",
					"Purchase Receipt Trends",
				],
			],
			"is_standard": "Yes",
		},
		"add_total_row",
		0,
	)
