from frappe import _

def get_data():
	return [
		{
			"label": _("Portal"),
			"items": [
				{
					"type": "doctype",
					"name": "Homepage",
					"description": _("Settings for website homepage"),
				},
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
