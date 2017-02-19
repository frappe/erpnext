frappe.query_reports["BOM Stock Report"] = {
    "filters": [
        {
            "fieldname":"bom",
            "label": __("BOM"),
            "fieldtype": "Link",
            "options": "BOM",
			"reqd": 1
        },{
            "fieldname":"warehouse",
            "label": __("Warehouse"),
            "fieldtype": "Link",
            "options": "Warehouse",
			"reqd": 1
        }
    ]
}
