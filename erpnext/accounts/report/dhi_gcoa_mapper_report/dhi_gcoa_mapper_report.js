// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["DHI GCOA Mapper Report"] = {
	"filters": [
		{
			"fieldname":"map",
			"fieldtype":"Select",
			"options":['GCOA Mapped\n','COA Unmapped\n'],
			"defaults":"GCOA Mapped",
			"on_change":(query_report)=>{
				var gcoa = query_report.filters_by_name["dhi_gcoa_acc"];
				var inter_company = query_report.filters_by_name["is_inter_company"];
				if  (query_report.get_values().map.trim() == 'COA Unmapped'){
					gcoa.toggle(false)
					// inter_company.toggle(true)
				}else{
					gcoa.toggle(true)
					// inter_company.toggle(false)
				}
				query_report.refresh()
			}
		},
		{
			"fieldname":"dhi_gcoa_acc",
			"label":"DHI GCOA",
			"fieldtype":"Link",
			"options":"DHI GCOA"
		},
		{
			"fieldname":"is_inter_company",
			"label":"Inter Company",
			"fieldtype":"Check",
			"default":1
		}
	]
};
