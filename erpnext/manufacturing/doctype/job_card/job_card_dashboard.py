from frappe import _


def get_data():
	return {
		"fieldname": "job_card",
		"non_standard_fieldnames": {"Quality Inspection": "reference_name"},
		"transactions": [
			{"label": _("Transactions"), "items": ["Material Request", "Stock Entry"]},
			{"label": _("Reference"), "items": ["Quality Inspection"]},
		],
	}
