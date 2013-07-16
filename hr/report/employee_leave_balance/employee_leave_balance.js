wn.query_reports["Employee Leave Balance"] = {
	"filters": [
		{
			"fieldname":"fiscal_year",
			"label": "Fiscal Year",
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": wn.defaults.get_user_default("fiscal_year")
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