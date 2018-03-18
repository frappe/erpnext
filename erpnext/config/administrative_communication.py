from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Doctypes"),
			"items": [
				{
					"type": "doctype",
					"name": "Administrative Decision",
					"description": _("Administrative Decision"),
				},
				
			]
		},
		{
			"label": _("Setup"),
			"items": [
				{
					"type": "doctype",
					"name": "Document Type",
					"description": _("Document Type"),
				},
			]
		}
	]
