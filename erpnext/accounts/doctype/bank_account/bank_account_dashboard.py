from frappe import _


def get_data():
	return {
		"fieldname": "bank_account",
		"non_standard_fieldnames": {
			"Customer": "default_bank_account",
			"Supplier": "default_bank_account",
		},
		"transactions": [
			{
				"label": _("Payments"),
				"items": ["Payment Entry", "Payment Request", "Payment Order", "Payroll Entry"],
			},
			{"label": _("Party"), "items": ["Customer", "Supplier"]},
			{"items": ["Bank Guarantee"]},
			{"items": ["Journal Entry"]},
		],
	}
