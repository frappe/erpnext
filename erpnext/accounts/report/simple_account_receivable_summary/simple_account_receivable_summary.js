/* eslint-disable */

frappe.query_reports["Simple Account Receivable Summary"] = {
	"filters": [
    		{
		    	"fieldname":"customer_name",
		    	"label": __("Name"),
		    	"fieldtype": "Link",
		    	'options': 'Customer',
		    	"reqd": 0
        	},
			{
		    	"fieldname":"address",
		    	"label": __("Address"),
		    	"fieldtype": "Data",
		    	"reqd": 0
        	},
			{
		    	"fieldname":"territory",
		    	"label": __("Territory"),
		    	"fieldtype": "Link",
		    	'options': 'Territory',
		    	"reqd": 0
        	},
			{
		    	"fieldname":"sales_person",
		    	"label": __("Sales Person"),
		    	"fieldtype": "Link",
		    	'options': 'Sales Person',
		    	"reqd": 0
        	},
			{
		    	"fieldname":"min_balance",
		    	"label": __("Skip Amount"),
		    	"fieldtype": "Int",
				"default":"5",
		    	"reqd": 0
        	},
			
	],

}

erpnext.utils.add_dimensions('Simple Account Receivable Summary', 9);
