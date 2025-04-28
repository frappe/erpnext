from frappe import _


def get_data():
	return {
		"fieldname": "production_plan",
<<<<<<< HEAD
		"non_standard_fieldnames": {
			"Stock Reservation Entry": "voucher_no",
		},
		"transactions": [
			{"label": _("Transactions"), "items": ["Work Order", "Material Request"]},
			{"label": _("Subcontract"), "items": ["Purchase Order"]},
			{"label": _("Reservation"), "items": ["Stock Reservation Entry"]},
=======
		"transactions": [
			{"label": _("Transactions"), "items": ["Work Order", "Material Request"]},
			{"label": _("Subcontract"), "items": ["Purchase Order"]},
>>>>>>> 7c4cf3e834 (Favicon.svg)
		],
	}
