from frappe import _


def get_data():
	return {
		"fieldname": "purchase_receipt_no",
		"non_standard_fieldnames": {
			"Purchase Invoice": "purchase_receipt",
			"Asset": "purchase_receipt",
			"Landed Cost Voucher": "receipt_document",
			"Auto Repeat": "reference_document",
			"Purchase Receipt": "return_against",
			"Stock Reservation Entry": "from_voucher_no",
		},
		"internal_links": {
			"Material Request": ["items", "material_request"],
			"Purchase Order": ["items", "purchase_order"],
			"Project": ["items", "project"],
			"Quality Inspection": ["items", "quality_inspection"],
		},
		"transactions": [
			{
				"label": _("Related"),
				"items": ["Purchase Invoice", "Landed Cost Voucher", "Asset", "Stock Reservation Entry"],
			},
			{
				"label": _("Reference"),
				"items": ["Material Request", "Purchase Order", "Quality Inspection", "Project"],
			},
			{"label": _("Returns"), "items": ["Purchase Receipt"]},
			{"label": _("Subscription"), "items": ["Auto Repeat"]},
		],
	}
