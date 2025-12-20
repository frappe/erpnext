from frappe import _


def get_data():
	return {
		"fieldname": "subcontracting_receipt",
		"non_standard_fieldnames": {
			"Subcontracting Receipt": "return_against",
		},
		"internal_links": {
			"Subcontracting Order": ["items", "subcontracting_order"],
			"Purchase Order": ["items", "purchase_order"],
			"Project": ["items", "project"],
			"Quality Inspection": ["items", "quality_inspection"],
		},
		"transactions": [
			{
				"label": _("Reference"),
				"items": [
					"Purchase Order",
					"Purchase Receipt",
					"Subcontracting Order",
					"Quality Inspection",
					"Project",
				],
			},
			{"label": _("Returns"), "items": ["Subcontracting Receipt"]},
		],
	}
