from frappe import _


# Todo: non_standard_fieldnames is to be decided
def get_data():
	return {
		"fieldname": "stock_entry",
		"non_standard_fieldnames": {
			"Stock Reservation Entry": "from_voucher_no",
			"Quality Inspection": "reference_name",
			"Quality Control Lot": "source_document",
		},
		"transactions": [
			{"label": _("Stock Reservation"), "items": ["Stock Reservation Entry"]},
			{"label": _("Quality"), "items": ["Quality Inspection", "Quality Control Lot"]},
		],
	}
