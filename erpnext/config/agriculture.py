from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Crops & Lands"),
			"items": [
				{
					"type": "doctype",
					"name": "Crop",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Crop Cycle",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Location",
					"onboard": 1,
				}
			]
		},
		{
			"label": _("Diseases & Fertilizers"),
			"items": [
				{
					"type": "doctype",
					"name": "Disease",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Fertilizer",
					"onboard": 1,
				}
			]
		},
		{
			"label": _("Analytics"),
			"items": [
				{
					"type": "doctype",
					"name": "Plant Analysis",
				},
				{
					"type": "doctype",
					"name": "Soil Analysis",
				},
				{
					"type": "doctype",
					"name": "Water Analysis",
				},
				{
					"type": "doctype",
					"name": "Soil Texture",
				},
				{
					"type": "doctype",
					"name": "Weather",
				},
				{
					"type": "doctype",
					"name": "Agriculture Analysis Criteria",
				}
			]
		},
	]