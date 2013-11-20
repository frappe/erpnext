// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

wn.module_page["Accounts"] = [
	{
		top: true,
		title: wn._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: wn._("Journal Voucher"),
				description: wn._("Accounting journal entries."),
				doctype:"Journal Voucher"
			},
			{
				label: wn._("Sales Invoice"),
				description: wn._("Bills raised to Customers."),
				doctype:"Sales Invoice"
			},
			{
				label: wn._("Purchase Invoice"),
				description: wn._("Bills raised by Suppliers."),
				doctype:"Purchase Invoice"
			},
		]
	},
	{
		title: wn._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: wn._("Chart of Accounts"),
				route: "Accounts Browser/Account",
				description: wn._("Structure of books of accounts."),
				doctype:"Account"
			},
			{
				label: wn._("Chart of Cost Centers"),
				route: "Accounts Browser/Cost Center",
				description: wn._("Structure cost centers for budgeting."),
				doctype:"Cost Center"
			},
			{
				label: wn._("Customer"),
				description: wn._("Customer database."),
				doctype:"Customer"
			},
			{
				label: wn._("Supplier"),
				description: wn._("Supplier database."),
				doctype:"Supplier"
			},
		]
	},
	{
		title: wn._("Setup"),
		icon: "icon-wrench",
		items: [
			{
				label: wn._("Company"),
				description: wn._("Company Master."),
				doctype:"Company"
			},
			{
				label: wn._("Fiscal Year"),
				description: wn._("Accounting Year."),
				doctype:"Fiscal Year"
			},
		]
	},
	{
		title: wn._("Tools"),
		icon: "icon-wrench",
		items: [
			{
				"route":"Form/Bank Reconciliation/Bank Reconciliation",
				"label": wn._("Bank Reconciliation"),
				"description": wn._("Update bank payment dates with journals."),
				doctype: "Bank Reconciliation"
			},
			{
				"route":"Form/Payment to Invoice Matching Tool/Payment to Invoice Matching Tool",
				"label": wn._("Payment Reconciliation"),
				"description": wn._("Match non-linked Invoices and Payments."),
				doctype: "Payment to Invoice Matching Tool"
				
			},
			{
				"label": wn._("Period Closing Voucher"),
				"doctype": "Period Closing Voucher",
				description: wn._("Close Balance Sheet and book Profit or Loss.")
			},
			{
				"page":"voucher-import-tool",
				"label": wn._("Voucher Import Tool"),
				"description": wn._("Import accounting entries from CSV.")
			},		
		]
	},
	{
		title: wn._("Setup"),
		icon: "icon-cog",
		items: [
			{
				"label": wn._("Accounts Settings"),
				"route": "Form/Accounts Settings",
				"doctype":"Accounts Settings",
				"description": wn._("Settings for Accounts")
			},
			{
				"label": wn._("Sales Taxes and Charges Master"),
				"doctype":"Sales Taxes and Charges Master",
				"description": wn._("Tax Template for Sales")
			},
			{
				"label": wn._("Purchase Taxes and Charges Master"),
				"doctype":"Purchase Taxes and Charges Master",
				"description": wn._("Tax Template for Purchase")
			},
			{
				"label": wn._("Shipping Rules"),
				"doctype":"Shipping Rule",
				"description": wn._("Rules to calculate shipping amount for a sale")
			},
			{
				"label": wn._("Currency Exchange"),
				"doctype":"Currency Exchange",
				"description": wn._("Manage exchange rates for currency conversion")
			},
			{
				"label": wn._("Point-of-Sale Setting"),
				"doctype":"POS Setting",
				"description": wn._("User settings for Point-of-sale (POS)")
			},
			{
				"doctype":"Budget Distribution",
				"label": wn._("Budget Distribution"),
				"description": wn._("Seasonality for setting budgets.")
			},
			{
				"doctype":"Terms and Conditions",
				"label": wn._("Terms and Conditions Template"),
				description: wn._("Template of terms or contract.")
			},
			{
				"doctype":"Mode of Payment",
				"label": wn._("Mode of Payment"),
				description: wn._("e.g. Bank, Cash, Credit Card")
			},
			{
				"doctype":"C-Form",
				"label": wn._("C-Form"),
				description: wn._("C-Form records"),
				country: "India"
			}
		]
	},
	{
		title: wn._("Main Reports"),
		right: true,
		icon: "icon-table",
		items: [
			{
				"label":wn._("General Ledger"),
				page: "general-ledger"
			},
			{
				"label":wn._("Trial Balance"),
				page: "trial-balance"
			},
			{
				"page":"Financial Statements",
				"label": wn._("Financial Statements")
			},
			{
				"label":wn._("Accounts Receivable"),
				route: "query-report/Accounts Receivable",
				doctype: "Sales Invoice"
			},
			{
				"label":wn._("Accounts Payable"),
				route: "query-report/Accounts Payable",
				doctype: "Purchase Invoice"
			},
			{
				"label":wn._("Sales Register"),
				route: "query-report/Sales Register",
				doctype: "Sales Invoice"
			},
			{
				"label":wn._("Purchase Register"),
				route: "query-report/Purchase Register",
				doctype: "Purchase Invoice"
			},
		]
	},
	{
		title: wn._("Analytics"),
		right: true,
		icon: "icon-bar-chart",
		items: [
			{
				"label":wn._("Financial Analytics"),
				page: "financial-analytics"
			},
			{
				"label":wn._("Gross Profit"),
				route: "query-report/Gross Profit",
				doctype: "Sales Invoice"
			},
		]
	},
	{
		title: wn._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":wn._("Bank Reconciliation Statement"),
				route: "query-report/Bank Reconciliation Statement",
				doctype: "Journal Voucher"
			},
			{
				"label":wn._("Ordered Items To Be Billed"),
				route: "query-report/Ordered Items To Be Billed",
				doctype: "Sales Invoice"
			},
			{
				"label":wn._("Delivered Items To Be Billed"),
				route: "query-report/Delivered Items To Be Billed",
				doctype: "Sales Invoice"
			},
			{
				"label":wn._("Purchase Order Items To Be Billed"),
				route: "query-report/Purchase Order Items To Be Billed",
				doctype: "Purchase Invoice"
			},
			{
				"label":wn._("Received Items To Be Billed"),
				route: "query-report/Received Items To Be Billed",
				doctype: "Purchase Invoice"
			},
			{
				"label":wn._("Bank Clearance Summary"),
				route: "query-report/Bank Clearance Summary",
				doctype: "Journal Voucher"
			},
			{
				"label":wn._("Payment Collection With Ageing"),
				route: "query-report/Payment Collection With Ageing",
				doctype: "Journal Voucher"
			},
			{
				"label":wn._("Payment Made With Ageing"),
				route: "query-report/Payment Made With Ageing",
				doctype: "Journal Voucher"
			},
			{
				"label":wn._("Sales Partners Commission"),
				route: "query-report/Sales Partners Commission",
				doctype: "Sales Invoice"
			},
			{
				"label":wn._("Customer Account Head"),
				route: "query-report/Customer Account Head",
				doctype: "Account"
			},
			{
				"label":wn._("Supplier Account Head"),
				route: "query-report/Supplier Account Head",
				doctype: "Account"
			},
			{
				"label":wn._("Item-wise Sales Register"),
				route: "query-report/Item-wise Sales Register",
				doctype: "Sales Invoice"
			},
			{
				"label":wn._("Item-wise Purchase Register"),
				route: "query-report/Item-wise Purchase Register",
				doctype: "Purchase Invoice"
			},
			{
				"label":wn._("Budget Variance Report"),
				route: "query-report/Budget Variance Report",
				doctype: "Cost Center"
			},
			{
				"label":wn._("Purchase Invoice Trends"),
				route: "query-report/Purchase Invoice Trends",
				doctype: "Purchase Invoice"
			},
			{
				"label":wn._("Sales Invoice Trends"),
				route: "query-report/Sales Invoice Trends",
				doctype: "Sales Invoice"
			},
		]
	}
]

pscript['onload_accounts-home'] = function(wrapper) {
	wn.views.moduleview.make(wrapper, "Accounts");
}