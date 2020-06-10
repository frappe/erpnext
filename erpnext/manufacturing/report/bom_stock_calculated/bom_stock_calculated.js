// Copyright (c) 2016, Epoch Consulting and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["BOM Stock Calculated"] = {
	"filters": [
		{
			"fieldname": "bom",
			"label": __("BOM"),
			"fieldtype": "Link",
			"options": "BOM",
			"reqd": 1
		},
        	{
	            "fieldname": "qty_to_make",
        	    "label": __("Quantity to Make"),
        	    "fieldtype": "Int",
        	    "default": "1"
	       },

		 {
			"fieldname": "show_exploded_view",
			"label": __("Show exploded view"),
			"fieldtype": "Check"
		}
	]
}
