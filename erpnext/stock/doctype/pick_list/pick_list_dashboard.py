from frappe import _


def get_data():
	return {
		"fieldname": "pick_list",
		"non_standard_fieldnames": {
			"Stock Reservation Entry": "from_voucher_no",
			"Delivery Note": "against_pick_list",
			"Sales Invoice": "against_pick_list",
		},
		"internal_links": {
			"Sales Order": ["locations", "sales_order"],
		},
		"transactions": [
			{
				"label": _("Sales"),
				"items": ["Sales Order", "Delivery Note", "Sales Invoice"],
			},
			{
				"label": _("Manufacturing"),
				"items": ["Stock Entry"],
			},
			{
				"label": _("Reference"),
				"items": ["Stock Reservation Entry"],
			},
		],
	}
