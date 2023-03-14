from frappe import _

def get_data():
	return {
        "fieldname": "repair_and_services",
		# "non_standard_fieldnames": {
		# 	"Repair And Service Invoice": "repair_and_services",
		# },
		# "internal_links": {
		# 	"EME Invoice": ["items", "logbook"],
		# },
		"transactions": [
			{"label": _("Related Transaction"), "items": ["Repair And Service Invoice","Material Request"]},
		],
	}
