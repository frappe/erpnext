from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Portal"),
			"items": [
				{
					"type": "doctype",
					"name": "Homepage",
					"label": _("Homepage"),
					"description": _("Settings for the website homepage"),
				},
				{
					"type": "doctype",
					"name": "Web Page Section",
					"label": _("Web Page Section"),
					"description": _("Add custom sections with cards on the homepage"),
				},
				{
					"type": "doctype",
					"name": "Web Page Card",
					"label": _("Web Page Card"),
					"description": _("Create and edit homepage cards"),
				},
				{
					"type": "doctype",
					"name": "Products Settings",
					"label": _("Products Settings"),
					"description": _("Settings for website product listing"),
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
