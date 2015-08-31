from frappe import _

def get_data():
	return [
		{
			"label": _("Shopping Cart"),
			"icon": "icon-wrench",
			"items": [
				{
					"type": "doctype",
					"name": "Shopping Cart Settings",
					"label": _("Shopping Cart Settings"),
					"description": _("Settings for online shopping cart such as shipping rules, price list etc."),
					"hide_count": True
				}
			]
		}
	]
