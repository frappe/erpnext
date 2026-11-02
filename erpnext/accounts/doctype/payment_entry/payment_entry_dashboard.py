from frappe import _


def get_data():
	return {
		"fieldname": "payment_entry",
		"non_standard_fieldnames": {"Journal Entry": "reference_name"},
		"transactions": [
			{"label": _("Accounting"), "items": ["Journal Entry"]},
		],
	}
