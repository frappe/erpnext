frappe.query_reports["Discrete Manufacture Costing"] = {
	"filters": [
		{
			"fieldname": "salesOrder",
			"label": __("Sales Order"),
            "fieldtype": "Link",
            "options": "Sales Order",
            "reqd": 1
        },
        {
			"fieldname": "productionPlan",
			"label": __("Production Plan"),
            "fieldtype": "Link",
			"options": "Production Plan",
			"reqd": 1,
			"get_query": function() {
				var saleOrder = frappe.query_report.get_values().salesOrder;
				if(!saleOrder)
					return
				
				return {
					"query": "erpnext.manufacturing.report.discrete_manufacture_costing.discrete_manufacture_costing.get_production_plan",
					"filters": {
						"sale_order": saleOrder
					}
				}
			}
        },
        // {
		// 	"fieldname": "stockEntryType",
		// 	"label": __("Stock Entry Type"),
        //     "fieldtype": "MultiSelectList",
        //     "default": "Manufacture",
		// 	get_data: function(txt) {
		// 		return frappe.db.get_link_options('Stock Entry Type', txt);
		// 	}
		// },
		{
			"fieldname": "itemGroup",
			"label": __("Item Group"),
            "fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Item Group', txt);
			}
        },
	]
}