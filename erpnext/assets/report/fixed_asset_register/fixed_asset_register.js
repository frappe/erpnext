// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Fixed Asset Register"] = {
	"filters": [
		{
			fieldname:"company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname:"status",
			label: __("Status"),
			fieldtype: "Select",
			options: "In Location\nDisposed",
			default: 'In Location',
			reqd: 1
		},
		{
			fieldname:"purchase_date",
			label: __("Purchase Date"),
			fieldtype: "Date"
		},
		{
			fieldname:"available_for_use_date",
			label: __("Available For Use Date"),
			fieldtype: "Date"
		},
		{
			fieldname:"asset_category",
			label: __("Asset Category"),
			fieldtype: "Link",
			options: "Asset Category"
		},
		{	
			fieldname:"finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book"
		},
		{
			fieldname:"cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center"
		},
		{
			fieldname:"finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book"
		},
		{
			fieldname:"group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: " \nAsset Category\nLocation",
			default: '',
		},
		{
			fieldname:"is_existing_asset",
			label: __("Is Existing Asset"),
			fieldtype: "Check"
		},
	]
};
