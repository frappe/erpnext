from frappe import _


def get_data():
	return {
		"non_standard_fieldnames": {
			"Purchase Receipt": "goods_inward_note",
			"Subcontracting Receipt": "goods_inward_note",
			"Quality Inspection": "reference_name",
		},
		"transactions": [
			{
				"label": _("Receipt"),
				"items": ["Purchase Receipt", "Subcontracting Receipt"],
			},
			{
				"label": _("Quality"),
				"items": ["Quality Inspection"],
			},
		],
	}
