/* eslint-disable */

frappe.query_reports["Day End Summary"] = {
	"filters": [
    		{
		    	"fieldname":"report_date",
		    	"label": __("Date"),
		    	"fieldtype": "Data",
		    	"default": frappe.datetime.get_today(),
		    	"reqd": 1
        	},
	],

}

erpnext.utils.add_dimensions('Day End Summary', 9);
