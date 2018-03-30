frappe.query_reports["BOM Stock Report"] = {
	"filters": [
		{
			"fieldname": "bom",
			"label": __("BOM"),
			"fieldtype": "Link",
			"options": "BOM",
			"reqd": 1
		}, {
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"reqd": 1
		}, {
			"fieldname": "show_exploded_view",
			"label": __("Show exploded view"),
			"fieldtype": "Check"
		}
	]
}
