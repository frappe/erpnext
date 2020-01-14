from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Settings"),
			"items": [
				{
					"type": "doctype",
					"name": "Marketplace Settings"
				},
			]
		},
		{
			"label": _("Marketplace"),
			"items": [
				{
					"type": "page",
					"name": "marketplace/home"
				},
			]
		},
	]