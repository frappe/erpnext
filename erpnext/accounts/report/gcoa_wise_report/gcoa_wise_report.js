// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GCOA Wise Report"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label":__("From Date"),
			"fieldtype":"Date",
			"reqd":1,
			"default":frappe.datetime.year_start()
		},
		{
			"fieldname":"to_date",
			"label":__("To Date"),
			"fieldtype":"Date",
			"reqd":1,
			"default":frappe.datetime.nowdate()
		},
		{
			"fieldname":"gcoa_name",
			"label":__("DHI GCOA Name"),
			"fieldtype":"Link",
			"options":'DHI GCOA Mapper',
			"on_change": (query_report)=>{
				account_name = query_report.get_values().gcoa_name
				frappe.call({
					method: "frappe.client.get",
					args:{
						doctype:'DHI GCOA Mapper',
						filters:{
							'name': account_name
						},
						fieldname:['account_code']
					},
					callback:(r)=>{
						query_report.filters_by_name.gcoa_code.set_input(r.message.account_code)
						// query_report.filters_by_name.is_inter_company.set_input(r.message.is_inter_company)
						query_report.trigger_refresh();
					}					
				})
			},
			"reqd":1
		},
		{
			"fieldname":"gcoa_code",
			"label":__("DHI GCOA Code"),
			"fieldtype":"Link",
			"options":'DHI GCOA',
			"read_only":1
		},
	]
}
