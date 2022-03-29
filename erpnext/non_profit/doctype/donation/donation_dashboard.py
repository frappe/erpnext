from frappe import _


def get_data():
	return {
		"fieldname": "donation",
		"non_standard_fieldnames": {"Payment Entry": "reference_name"},
		"transactions": [{"label": _("Payment"), "items": ["Payment Entry"]}],
	}
