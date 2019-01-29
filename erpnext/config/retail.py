from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
            "label": _("Retail Operations"),
            "items": [
                {
                    "type": "page",
                    "name": "pos",
                    "label": _("POS"),
                    "description": _("Point of Sale")
                },
                {
                    "type": "doctype",
                    "name": "Cashier Closing",
                    "description": _("Cashier Closing")
                },
                {
                    "type": "doctype",
                    "name": "POS Settings",
                    "description": _("Setup mode of POS (Online / Offline)")
                },
                {
                    "type": "doctype",
                    "name": "POS Profile",
                    "label": _("Point-of-Sale Profile"),
                    "description": _("Setup default values for POS Invoices")
                },
                {
                    "type": "doctype",
                    "name": "Loyalty Program",
                    "label": _("Loyalty Program"),
                    "description": _("To make Customer based incentive schemes.")
                },
                {
                    "type": "doctype",
                    "name": "Loyalty Point Entry",
                    "label": _("Loyalty Point Entry"),
                    "description": _("To view logs of Loyalty Points assigned to a Customer.")
                }
            ]
        }
	]