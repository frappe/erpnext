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
				},
				{
					"type": "doctype",
					"name": "Crop Cycle",
				},
				{
					"type": "doctype",
					"name": "Location"
				}
			]
		},
		{
			"label": _("Diseases & Fertilizers"),
			"items": [
				{
					"type": "doctype",
					"name": "Disease",
				},
				{
					"type": "doctype",
					"name": "Fertilizer",
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
		{
			"label": _("Settings"),
			"items": [
				{
					"type": "doctype",
					"name": "Agriculture Settings",
				},
			]
		},
	]