// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Fleet Engagement Report"] = {
	"filters": [
		{
			fieldname:"from_date",
			label:"From Date",
			fieldtype:"Date",
			reqd:1,
			default:frappe.datetime.month_start()
		},
		{
			fieldname:"to_date",
			label:"To Date",
			fieldtype:"Date",
			reqd:1,
			default:frappe.datetime.month_end()
		},
		{
			fieldname:"equipment",
			label:"Equipment",
			fieldtype:"Link",
			options:"Equipment",
			"get_query": function() {return {'filters':{
				hired_equipment:0,
				enabled:1
			}}}
		},
		{
			fieldname:"branch",
			label:"Branch",
			fieldtype:"Link",
			options:"Branch",
		},
		{
			fieldname:"aggregate",
			label:"Aggregate Data",
			fieldtype:"Check",
			default:1
		},
	]
};
