from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Article"),
			"items": [
				{
					"type": "doctype",
					"name": "Article"
				}
			]
		}
	]
