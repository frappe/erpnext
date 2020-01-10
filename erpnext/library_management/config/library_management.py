from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
	  {
		"label":_("Library"),
		"icon": "octicon octicon-briefcase",
		"items": [
			{
			  "type": "doctype",
			  "name": "Article",
			  "label": _("Article"),
			  "description": _("Articles which members issue and return."),
			},
		  ]
	  }
  ]
