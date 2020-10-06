from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Vehicle Masters"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle",
					"description": _("Vehicle List."),
					"onboard": 1,
				},
			]
		},
	]