// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

wn.query_reports["Customers Not Buying Since Long Time"] = {
	"filters": [
		{
			"fieldname":"days_since_last_order",
			"label": "Days Since Last Order",
			"fieldtype": "Int",
			"default": 60
		}
	]
}