from frappe import _


def get_data():
	return {
		"fieldname": "item_tax_template",
		"transactions": [
			{"label": _("Pre Sales"), "items": ["Quotation", "Supplier Quotation"]},
			{"label": _("Sales"), "items": ["Sales Invoice", "Sales Order", "Delivery Note"]},
			{"label": _("Purchase"), "items": ["Purchase Invoice", "Purchase Order", "Purchase Receipt"]},
			{"label": _("Stock"), "items": ["Item Groups", "Item"]},
		],
	}
