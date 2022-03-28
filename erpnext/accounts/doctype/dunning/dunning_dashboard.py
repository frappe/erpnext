from frappe import _


def get_data():
	return {
		"fieldname": "dunning",
		"non_standard_fieldnames": {
			"Journal Entry": "reference_name",
			"Payment Entry": "reference_name",
		},
		"transactions": [{"label": _("Payment"), "items": ["Payment Entry", "Journal Entry"]}],
	}
