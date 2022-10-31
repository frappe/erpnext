from frappe import _


def get_data():
	return {
		"fieldname": "material_request",
		"internal_links": {
			"Sales Order": ["items", "sales_order"],
		},
		"transactions": [
			{
				"label": _("Reference"),
				"items": ["Sales Order", "Request for Quotation", "Supplier Quotation", "Purchase Order"],
			},
			{"label": _("Stock"), "items": ["Stock Entry", "Purchase Receipt", "Pick List"]},
			{"label": _("Manufacturing"), "items": ["Work Order"]},
		],
	}
