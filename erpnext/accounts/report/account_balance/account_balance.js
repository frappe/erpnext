// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Account Balance"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "report_date",
			label: __("Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "root_type",
			label: __("Root Type"),
			fieldtype: "Select",
			options: [
				{ value: "Asset", label: __("Asset") },
				{ value: "Liability", label: __("Liability") },
				{ value: "Income", label: __("Income") },
				{ value: "Expense", label: __("Expense") },
				{ value: "Equity", label: __("Equity") },
			],
		},
		{
			fieldname: "account_type",
			label: __("Account Type"),
			fieldtype: "Select",
			options: [
				{ value: "Accumulated Depreciation", label: __("Accumulated Depreciation") },
				{ value: "Asset Received But Not Billed", label: __("Asset Received But Not Billed") },
				{ value: "Bank", label: __("Bank") },
				{ value: "Cash", label: __("Cash") },
				{ value: "Chargeble", label: __("Chargeble") },
				{ value: "Capital Work in Progress", label: __("Capital Work in Progress") },
				{ value: "Cost of Goods Sold", label: __("Cost of Goods Sold") },
				{ value: "Depreciation", label: __("Depreciation") },
				{ value: "Equity", label: __("Equity") },
				{ value: "Expense Account", label: __("Expense Account") },
				{
					value: "Expenses Included In Asset Valuation",
					label: __("Expenses Included In Asset Valuation"),
				},
				{ value: "Expenses Included In Valuation", label: __("Expenses Included In Valuation") },
				{ value: "Fixed Asset", label: __("Fixed Asset") },
				{ value: "Income Account", label: __("Income Account") },
				{ value: "Payable", label: __("Payable") },
				{ value: "Receivable", label: __("Receivable") },
				{ value: "Round Off", label: __("Round Off") },
				{ value: "Stock", label: __("Stock") },
				{ value: "Stock Adjustment", label: __("Stock Adjustment") },
				{ value: "Stock Received But Not Billed", label: __("Stock Received But Not Billed") },
				{ value: "Tax", label: __("Tax") },
				{ value: "Temporary", label: __("Temporary") },
			],
		},
	],
};
