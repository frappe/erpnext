// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["General Ledger"] = {
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
			"fieldname":"account",
			"label": wn._("Account"),
			"fieldtype": "Link",
			"options": "Account"
		},
		{
			"fieldname":"voucher_no",
			"label": wn._("Voucher No"),
			"fieldtype": "Data",
		},
		{
			"fieldname":"group_by",
			"label": wn._("Group by"),
			"fieldtype": "Select",
			"options": "\nGroup by Account\nGroup by Voucher"
		},
		{
			"fieldtype": "Break",
		},
		{
			"fieldname":"from_date",
			"label": wn._("From Date"),
			"fieldtype": "Date",
			"default": wn.datetime.add_months(wn.datetime.get_today(), -1),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"to_date",
			"label": wn._("To Date"),
			"fieldtype": "Date",
			"default": wn.datetime.get_today(),
			"reqd": 1,
			"width": "60px"
		}
	]
}