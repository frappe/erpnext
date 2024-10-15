from frappe import _


def get_data():
	return {
		"fieldname": "work_order",
		"non_standard_fieldnames": {
			"Batch": "reference_name",
			"Stock Reservation Entry": "voucher_no",
		},
		"transactions": [
			{"label": _("Transactions"), "items": ["Stock Entry", "Job Card", "Pick List"]},
			{"label": _("Reference"), "items": ["Serial No", "Batch", "Material Request"]},
			{"label": _("Stock Reservation"), "items": ["Stock Reservation Entry"]},
		],
	}
