from frappe import _


# Todo: non_standard_fieldnames is to be decided
def get_data():
	return {
		"fieldname": "stock_entry",
		"non_standard_fieldnames": {
<<<<<<< HEAD
			"Stock Reservation Entry": "from_voucher_no",
		},
		"transactions": [
			{"label": _("Stock Reservation"), "items": ["Stock Reservation Entry"]},
=======
			# "DocType Name": "Reference field name",
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
>>>>>>> 7c4cf3e834 (Favicon.svg)
		],
	}
