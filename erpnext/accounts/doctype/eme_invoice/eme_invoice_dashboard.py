from frappe import _

def get_data():
	return {
        "fieldname": "reference_name",
		"non_standard_fieldnames": {
			"Journal Entry": "referece_doctype"
		},
		"transactions": [
			{"label": _("Related Transaction"), "items": ["Journal Entry"]},
		],
	}