from frappe import _


def get_data():
	return {
		"fieldname": "bom_no",
		"non_standard_fieldnames": {
			"Item": "default_bom",
			"Purchase Order": "bom",
		},
		"transactions": [
			{"label": _("Stock"), "items": ["Item", "Stock Entry", "Quality Inspection"]},
			{"label": _("Manufacture"), "items": ["BOM", "Work Order", "Job Card"]},
			{
				"label": _("Subcontract"),
				"items": ["Purchase Order"],
			},
		],
		"disable_create_buttons": [
			"Item",
			"Purchase Order",
			"Job Card",
			"Stock Entry",
			"BOM",
		],
	}
