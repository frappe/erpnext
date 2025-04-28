from frappe import _


def get_data():
	return {
		"fieldname": "subcontracting_order",
<<<<<<< HEAD
		"non_standard_fieldnames": {"Stock Reservation Entry": "voucher_no"},
		"transactions": [
			{
				"label": _("Reference"),
				"items": ["Subcontracting Receipt", "Stock Entry"],
			},
			{
				"label": _("Stock Reservation"),
				"items": ["Stock Reservation Entry"],
			},
		],
=======
		"transactions": [{"label": _("Reference"), "items": ["Subcontracting Receipt", "Stock Entry"]}],
>>>>>>> 7c4cf3e834 (Favicon.svg)
	}
