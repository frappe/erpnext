// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Stock Ageing"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": wn._("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": wn.defaults.get_user_default("company"),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": wn._("To Date"),
			"fieldtype": "Date",
			"default": wn.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"warehouse",
			"label": wn._("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname":"item_code",
			"label": wn._("Item"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname":"brand",
			"label": wn._("Brand"),
			"fieldtype": "Link",
			"options": "Brand"
		}
	]
}