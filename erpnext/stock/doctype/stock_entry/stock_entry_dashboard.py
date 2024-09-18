from frappe import _


# Todo: non_standard_fieldnames is to be decided
def get_data():
	return {
		"fieldname": "stock_entry",
		"non_standard_fieldnames": {
			"Stock Reservation Entry": "from_voucher_no",
		},
		"internal_links": {
			"Purchase Order": ["items", "purchase_order"],
			"Subcontracting Order": ["items", "subcontracting_order"],
			"Subcontracting Receipt": ["items", "subcontracting_receipt"],
		},
		"transactions": [
			{
				"label": _("Reference"),
				"items": [
					"Purchase Order",
					"Subcontracting Order",
					"Subcontracting Receipt",
				],
			},
			{"label": _("Stock Reservation"), "items": ["Stock Reservation Entry"]},
		],
	}
