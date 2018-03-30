from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Setup"),
			"items": [
				{
					"type": "doctype",
					"name": "Hub Settings"
				},
			]
		},
		{
			"label": _("Hub"),
			"items": [
				{
					"type": "page",
					"name": "hub"
				},
			]
		},
	]