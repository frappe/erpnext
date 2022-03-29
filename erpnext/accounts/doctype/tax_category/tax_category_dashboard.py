from frappe import _


def get_data():
	return {
		"fieldname": "tax_category",
		"transactions": [
			{"label": _("Pre Sales"), "items": ["Quotation", "Supplier Quotation"]},
			{"label": _("Sales"), "items": ["Sales Invoice", "Delivery Note", "Sales Order"]},
			{"label": _("Purchase"), "items": ["Purchase Invoice", "Purchase Receipt"]},
			{"label": _("Party"), "items": ["Customer", "Supplier"]},
			{"label": _("Taxes"), "items": ["Item", "Tax Rule"]},
		],
	}
