wn.query_reports["Daily Time Log Summary"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"default": wn.datetime.get_today()
		},
		{
			"fieldname":"to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"default": wn.datetime.get_today()
		},
	]
}