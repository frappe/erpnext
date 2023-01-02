from frappe import _

def get_data():
	return {
        "fieldname": "reference",
		"transactions": [
			{"label": _("Production"), "items": ["Production"]},
		],
	}