wn.query_reports["Gross Profit"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": "Company",
			"fieldtype": "Link",
			"options": "Company",
			"default": wn.defaults.get_user_default("company")
		}
	]
}