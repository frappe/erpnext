from frappe import _


def get_data():
	return {
		"fieldname": "subcontracting_receipt",
		"non_standard_fieldnames": {
			"Subcontracting Receipt": "return_against",
			"Quality Control Lot": "source_document",
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
					"Quality Control Lot",
					"Project",
				],
			},
			{"label": _("Returns"), "items": ["Subcontracting Receipt"]},
		],
	}
