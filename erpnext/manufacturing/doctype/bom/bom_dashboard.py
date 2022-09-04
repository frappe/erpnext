from frappe import _


def get_data():
	return {
		"fieldname": "bom_no",
		"non_standard_fieldnames": {
			"Item": "default_bom",
			"Purchase Order": "bom",
			"Purchase Receipt": "bom",
			"Purchase Invoice": "bom",
		},
		"transactions": [
			{"label": _("Stock"), "items": ["Item", "Stock Entry", "Quality Inspection"]},
			{"label": _("Manufacture"), "items": ["BOM", "Work Order", "Job Card"]},
			{
				"label": _("Subcontract"),
				"items": ["Purchase Order", "Purchase Receipt", "Purchase Invoice"],
			},
		],
		"disable_create_buttons": [
			"Item",
			"Purchase Order",
			"Purchase Receipt",
			"Purchase Invoice",
			"Job Card",
			"Stock Entry",
			"BOM",
		],
	}
