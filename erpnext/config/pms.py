from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
     
        	{
			"label": _("Master"),
			"icon": "fa fa-list",
			"items": [
				    {
			           "type": "doctype",
					   "name": "PMS Group",
					   "onboard": 1
					},
                    {
					    "type": "doctype",
					   "name": "Work Competency",
					   "onboard": 1
					},
                    
                    {
					    "type": "doctype",
					   "name": "Employee Category",
					   "onboard": 1
					},
                    
                    
        		
			]
		  },
		{
			"label": _("PMS"),
			"items": [
				{
					"type": "doctype",
					"name": "PMS Calendar",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Target Set Up",
					"label": ("Target Setup"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Work Competency",
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Employee Category",
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Review",
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Performance Evaluation",
					"onboard": 1
				},

			]
		},
		
		
		{
			"label": _("Reports"),
			"icon": "fa fa-list",
			"items": [
				    # {
					# 	"type": "report",
					# 	"is_query_report": True,
					# 	"name": "Target Setup Report",
					# 	"label": _("Target Setup Report"),
					# 	"doctype": "Target Set Up"
					# },
                    {
						"type": "report",
						"is_query_report": True,
						"name": "PMS Report",
						"label": _("PMS Report"),
						"doctype": "Target Set Up"
					},		
        		
			]
		},
  
      
        
	]
