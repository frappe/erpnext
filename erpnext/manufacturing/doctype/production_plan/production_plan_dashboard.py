from frappe import _


def get_data():
	return {
		"fieldname": "production_plan",
		"transactions": [
			{"label": _("Transactions"), "items": ["Work Order", "Material Request"]},
			{"label": _("Subcontract"), "items": ["Purchase Order"]},
		],
	}
