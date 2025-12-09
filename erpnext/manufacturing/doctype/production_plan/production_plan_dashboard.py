from frappe import _


def get_data():
	return {
		"fieldname": "production_plan",
		"transactions": [
			{"label": _("Transactions"), "items": ["Work Order", "Material Request"]},
			# {"label": _("Daily Plans"), "items": ["Sales Order"]},
			{"label": _("Subcontract"), "items": ["Purchase Order"]},
		],
	}
