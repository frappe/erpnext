from frappe import _


def get_data():
	return {
		"fieldname": "payment_terms_template",
		"non_standard_fieldnames": {
			"Customer Group": "payment_terms",
			"Supplier Group": "payment_terms",
			"Supplier": "payment_terms",
			"Customer": "payment_terms",
		},
		"transactions": [
			{"label": _("Sales"), "items": ["Sales Invoice", "Sales Order", "Quotation"]},
			{"label": _("Purchase"), "items": ["Purchase Invoice", "Purchase Order"]},
			{"label": _("Party"), "items": ["Customer", "Supplier"]},
			{"label": _("Group"), "items": ["Customer Group", "Supplier Group"]},
		],
	}
