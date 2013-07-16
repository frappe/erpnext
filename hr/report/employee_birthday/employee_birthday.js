wn.query_reports["Employee Birthday"] = {
	"filters": [
		{
			"fieldname":"month",
			"label": "Month",
			"fieldtype": "Select",
			"options": "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
			"default": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
				"Dec"][wn.datetime.str_to_obj(wn.datetime.get_today()).getMonth()],
		},
		{
			"fieldname":"company",
			"label": "Company",
			"fieldtype": "Link",
			"options": "Company",
			"default": wn.defaults.get_user_default("company")
		}
	]
}