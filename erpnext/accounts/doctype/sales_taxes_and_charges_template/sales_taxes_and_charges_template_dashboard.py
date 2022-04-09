from frappe import _


def get_data():
	return {
		"fieldname": "taxes_and_charges",
		"non_standard_fieldnames": {
			"Tax Rule": "sales_tax_template",
			"Subscription": "sales_tax_template",
			"Restaurant": "default_tax_template",
		},
		"transactions": [
			{"label": _("Transactions"), "items": ["Sales Invoice", "Sales Order", "Delivery Note"]},
			{"label": _("References"), "items": ["POS Profile", "Subscription", "Restaurant", "Tax Rule"]},
		],
	}
