wn.query_reports["Warehouse-Wise Stock Balance"] = {
	"filters": [
		{
			"fieldname":"item_code",
			"label": "Item",
			"fieldtype": "Link",
			"options": "Item",
			"width": "80"
		},
		{
			"fieldname":"warehouse",
			"label": "Warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": "80"
		},
		{
			"fieldname":"from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"width": "80",
			"default": sys_defaults.year_start_date,
		},
		{
			"fieldname":"to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"width": "80",
			"default": wn.datetime.get_today()
		}
	]
}