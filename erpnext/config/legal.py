from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Law"),
			"items": [
				{
					"type": "doctype",
					"name": "Law"
				}
			]
		}
	]
