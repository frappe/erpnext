// Copyright (c) 2016, Epoch and contributors
// For license information, please see license.txt

frappe.query_reports["BOM Item Warehouse"] = {
	"filters": [

	        {
                        "fieldname":"bom",
                        "label": __("BOM"),
                        "fieldtype": "Link",
                        "options": "BOM",
			"reqd": 1
                        
                },
                
		{
                        "fieldname":"company",
                        "label": __("Company"),
                        "fieldtype": "Link",
                        "options": "Company",
			"reqd": 1
                        
                },
                {      "fieldname":"from_date",
                        "label": __("From Date"),
                        "fieldtype": "Date",
                        "width": "80",
                        "default": sys_defaults.year_start_date,
                },
                {
                        "fieldname":"to_date",
                        "label": __("To Date"),
                        "fieldtype": "Date",
                        "width": "80",
                        "default": frappe.datetime.get_today()
                },
                {
                        "fieldname":"warehouse",
                        "label": __("Warehouse"),
                        "fieldtype": "Link",
                        "options": "Warehouse",
			"reqd": 1
                },
                {
                        "fieldname":"item_code",
                        "label": __("Item"),
                        "fieldtype": "Link",
                        "options": "Item"
                },
                       
		{
			"fieldname":"include_exploded_items",
			"label": __("Include Exploded Items"),
			"fieldtype": "Data",
                        "default": "Y"
			
		}          
                
        ]
}

// $(function() {
//      $(wrapper).bind("show", function() {
//              frappe.query_report.load();
//      });
// });

