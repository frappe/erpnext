// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["EME Invoice Details"] = {
	"filters": [
		{
			"fieldname":"name",
			"label":__("Reference"),
			"fieldtype":"Link",
			"options":"EME Invoice",
			"reqd":1
		}
	]
};
