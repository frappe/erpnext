from frappe import _


def get_data():
	return {
		"fieldname": "stock_closing_entry",
		"transactions": [
			{
				"label": _("Stock Closing Log"),
				"items": ["Stock Closing Balance"],
			},
		],
	}
