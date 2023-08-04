from frappe import _


def get_data():
	return {
		"fieldname": "batch_no",
		"transactions": [
			{"label": _("Buy"), "items": ["Purchase Invoice", "Purchase Receipt"]},
			{"label": _("Sell"), "items": ["Sales Invoice", "Delivery Note"]},
			{"label": _("Move"), "items": ["Serial and Batch Bundle"]},
			{"label": _("Quality"), "items": ["Quality Inspection"]},
		],
	}
