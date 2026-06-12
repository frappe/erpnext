from frappe import _


def get_data():
	return {
		# the default link field; without one the form never asks for counts
		"fieldname": "goods_inward_note",
		"non_standard_fieldnames": {
			"Quality Inspection": "reference_name",
		},
		"transactions": [
			{
				"label": _("Receipt"),
				"items": ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"],
			},
			{
				"label": _("Quality"),
				"items": ["Quality Inspection"],
			},
		],
	}
