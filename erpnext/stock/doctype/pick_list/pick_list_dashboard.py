def get_data():
	return {
		"fieldname": "pick_list",
		"non_standard_fieldnames": {
			"Stock Reservation Entry": "from_voucher_no",
<<<<<<< HEAD
			"Delivery Note": "against_pick_list",
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		},
		"internal_links": {
			"Sales Order": ["locations", "sales_order"],
		},
		"transactions": [
			{"items": ["Stock Entry", "Sales Order", "Delivery Note", "Stock Reservation Entry"]},
		],
	}
