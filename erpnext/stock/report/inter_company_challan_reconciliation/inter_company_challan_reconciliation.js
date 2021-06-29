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
			fieldname: "stock_entry",
			label: __("Inward Challan"),
			fieldtype: "Link",
			options:"Stock Entry",
			default: "",
			reqd: 0,
			get_query: () => {
				return {
					filters: {
						'stock_entry_type':"Material Receipt"
					}
				};
			}
		},
		{
			fieldname: "reference_challan",
			label: __("Outward Challan"),
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
			fieldname: "item_code",
			label: __("Inward Item Code"),
			fieldtype: "Link",
			options:"Item",
			reqd: 0
		},
		{
			fieldname: "item_code",
			label: __("Outward Item Code"),
			fieldtype: "Link",
			options:"Item",
			default: "",
			reqd: 0
		},
		{
			fieldname: "batch_no",
			label: __("Inward Batch Number"),
			fieldtype: "Link",
			options:"Batch",
			default: "",
			reqd: 0
		},
		{
			fieldname: "batch_no",
			label: __("Outward Batch Number"),
			fieldtype: "Link",
			options:"Batch",
			default: "",
			reqd: 0
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
