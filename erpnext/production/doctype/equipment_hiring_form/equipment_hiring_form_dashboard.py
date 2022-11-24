from frappe import _

def get_data():
	return {
        "fieldname": "equipment_hiring_form",
		"transactions": [
			{"label": _("Transaction"), "items": ["Logbook"]},
		],
	}
