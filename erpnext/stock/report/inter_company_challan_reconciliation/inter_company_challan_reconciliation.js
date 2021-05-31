// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Inter Company Challan Reconciliation"] = {
	"filters": [
        {
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options:"Company",
			reqd: 1
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options:"Item",
			reqd: 0
		},
		// {
		// 	fieldname: "intercompany_item",
		// 	label: __("Intercompany Item"),
		// 	fieldtype: "Link",
		// 	options:"Item",
		// 	default: "",
		// 	reqd: 0
		// },
		{
			fieldname: "batch_no",
			label: __("Batch Number"),
			fieldtype: "Link",
			options:"Batch",
			default: "",
			reqd: 0
		},
		{
			fieldname: "stock_entry",
			label: __("Stock Entry"),
			fieldtype: "Link",
			options:"Stock Entry",
			default: "",
			reqd: 0
		},
		{
			fieldname: "reference_challan",
			label: __("Reference Challan"),
			fieldtype: "Link",
			options:"Stock Entry",
			default: "",
			reqd: 0,
			get_query: () => {
				return {
					filters: {
						'stock_entry_type':"Send to Subcontractor"
					}
				};
			}
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 0
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 0
        },
	]
};
