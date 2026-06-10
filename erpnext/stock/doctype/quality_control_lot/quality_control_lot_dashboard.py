from frappe import _


def get_data():
	return {
		"fieldname": "quality_control_lot",
		"non_standard_fieldnames": {
			"Quality Inspection": "reference_name",
		},
		"transactions": [
			{
				"label": _("Quality"),
				"items": ["Quality Inspection", "Stock Entry"],
			},
		],
	}
