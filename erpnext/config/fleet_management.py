from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Fleet Management"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle",
					"description": _("Vehicle")
				},
				{
					"type": "doctype",
					"name": "Vehicle Log",
					"description": _("Vehicle Log")
				}
			]
		}
	]