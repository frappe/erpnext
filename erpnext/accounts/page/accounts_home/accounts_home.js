// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

frappe.module_page["Accounts"] = [
	{
		top: true,
		title: frappe._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: frappe._("Journal Voucher"),
				description: frappe._("Accounting journal entries."),
				doctype:"Journal Voucher"
			},
			{
				label: frappe._("Sales Invoice"),
				description: frappe._("Bills raised to Customers."),
				doctype:"Sales Invoice"
			},
			{
				label: frappe._("Purchase Invoice"),
				description: frappe._("Bills raised by Suppliers."),
				doctype:"Purchase Invoice"
			},
		]
	},
	{
		title: frappe._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: frappe._("Chart of Accounts"),
				route: "Accounts Browser/Account",
				description: frappe._("Structure of books of accounts."),
				doctype:"Account"
			},
			{
				label: frappe._("Chart of Cost Centers"),
				route: "Accounts Browser/Cost Center",
				description: frappe._("Structure cost centers for budgeting."),
				doctype:"Cost Center"
			},
			{
				label: frappe._("Customer"),
				description: frappe._("Customer database."),
				doctype:"Customer"
			},
			{
				label: frappe._("Supplier"),
				description: frappe._("Supplier database."),
				doctype:"Supplier"
			},
		]
	},
	{
		title: frappe._("Setup"),
		icon: "icon-wrench",
		items: [
			{
				label: frappe._("Company"),
				description: frappe._("Company Master."),
				doctype:"Company"
			},
			{
				label: frappe._("Fiscal Year"),
				description: frappe._("Accounting Year."),
				doctype:"Fiscal Year"
			},
		]
	},
	{
		title: frappe._("Tools"),
		icon: "icon-wrench",
		items: [
			{
				"route":"Form/Bank Reconciliation/Bank Reconciliation",
				"label": frappe._("Bank Reconciliation"),
				"description": frappe._("Update bank payment dates with journals."),
				doctype: "Bank Reconciliation"
			},
			{
				"route":"Form/Payment to Invoice Matching Tool/Payment to Invoice Matching Tool",
				"label": frappe._("Payment Reconciliation"),
				"description": frappe._("Match non-linked Invoices and Payments."),
				doctype: "Payment to Invoice Matching Tool"
				
			},
			{
				"label": frappe._("Period Closing Voucher"),
				"doctype": "Period Closing Voucher",
				description: frappe._("Close Balance Sheet and book Profit or Loss.")
			},
		]
	},
	{
		title: frappe._("Setup"),
		icon: "icon-cog",
		items: [
			{
				"label": frappe._("Accounts Settings"),
				"route": "Form/Accounts Settings",
				"doctype":"Accounts Settings",
				"description": frappe._("Settings for Accounts")
			},
			{
				"label": frappe._("Sales Taxes and Charges Master"),
				"doctype":"Sales Taxes and Charges Master",
				"description": frappe._("Tax Template for Sales")
			},
			{
				"label": frappe._("Purchase Taxes and Charges Master"),
				"doctype":"Purchase Taxes and Charges Master",
				"description": frappe._("Tax Template for Purchase")
			},
			{
				"label": frappe._("Shipping Rules"),
				"doctype":"Shipping Rule",
				"description": frappe._("Rules to calculate shipping amount for a sale")
			},
			{
				"label": frappe._("Currency Exchange"),
				"doctype":"Currency Exchange",
				"description": frappe._("Manage exchange rates for currency conversion")
			},
			{
				"label": frappe._("Point-of-Sale Setting"),
				"doctype":"POS Setting",
				"description": frappe._("User settings for Point-of-sale (POS)")
			},
			{
				"doctype":"Budget Distribution",
				"label": frappe._("Budget Distribution"),
				"description": frappe._("Seasonality for setting budgets.")
			},
			{
				"doctype":"Terms and Conditions",
				"label": frappe._("Terms and Conditions Template"),
				description: frappe._("Template of terms or contract.")
			},
			{
				"doctype":"Mode of Payment",
				"label": frappe._("Mode of Payment"),
				description: frappe._("e.g. Bank, Cash, Credit Card")
			},
			{
				"doctype":"C-Form",
				"label": frappe._("C-Form"),
				description: frappe._("C-Form records"),
				country: "India"
			}
		]
	},
	{
		title: frappe._("Main Reports"),
		right: true,
		icon: "icon-table",
		items: [
			{
				"label":frappe._("General Ledger"),
				doctype: "GL Entry",
				route: "query-report/General Ledger"
			},
			{
				"label":frappe._("Trial Balance"),
				page: "trial-balance"
			},
			{
				"page":"Financial Statements",
				"label": frappe._("Financial Statements")
			},
			{
				"label":frappe._("Accounts Receivable"),
				route: "query-report/Accounts Receivable",
				doctype: "Sales Invoice"
			},
			{
				"label":frappe._("Accounts Payable"),
				route: "query-report/Accounts Payable",
				doctype: "Purchase Invoice"
			},
			{
				"label":frappe._("Sales Register"),
				route: "query-report/Sales Register",
				doctype: "Sales Invoice"
			},
			{
				"label":frappe._("Purchase Register"),
				route: "query-report/Purchase Register",
				doctype: "Purchase Invoice"
			},
		]
	},
	{
		title: frappe._("Analytics"),
		right: true,
		icon: "icon-bar-chart",
		items: [
			{
				"label":frappe._("Financial Analytics"),
				page: "financial-analytics"
			},
			{
				"label":frappe._("Gross Profit"),
				route: "query-report/Gross Profit",
				doctype: "Sales Invoice"
			},
		]
	},
	{
		title: frappe._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":frappe._("Bank Reconciliation Statement"),
				route: "query-report/Bank Reconciliation Statement",
				doctype: "Journal Voucher"
			},
			{
				"label":frappe._("Ordered Items To Be Billed"),
				route: "query-report/Ordered Items To Be Billed",
				doctype: "Sales Invoice"
			},
			{
				"label":frappe._("Delivered Items To Be Billed"),
				route: "query-report/Delivered Items To Be Billed",
				doctype: "Sales Invoice"
			},
			{
				"label":frappe._("Purchase Order Items To Be Billed"),
				route: "query-report/Purchase Order Items To Be Billed",
				doctype: "Purchase Invoice"
			},
			{
				"label":frappe._("Received Items To Be Billed"),
				route: "query-report/Received Items To Be Billed",
				doctype: "Purchase Invoice"
			},
			{
				"label":frappe._("Bank Clearance Summary"),
				route: "query-report/Bank Clearance Summary",
				doctype: "Journal Voucher"
			},
			{
				"label":frappe._("Payment Period Based On Invoice Date"),
				route: "query-report/Payment Period Based On Invoice Date",
				doctype: "Journal Voucher"
			},
			{
				"label":frappe._("Sales Partners Commission"),
				route: "query-report/Sales Partners Commission",
				doctype: "Sales Invoice"
			},
			{
				"label":frappe._("Customer Account Head"),
				route: "query-report/Customer Account Head",
				doctype: "Account"
			},
			{
				"label":frappe._("Supplier Account Head"),
				route: "query-report/Supplier Account Head",
				doctype: "Account"
			},
			{
				"label":frappe._("Item-wise Sales Register"),
				route: "query-report/Item-wise Sales Register",
				doctype: "Sales Invoice"
			},
			{
				"label":frappe._("Item-wise Purchase Register"),
				route: "query-report/Item-wise Purchase Register",
				doctype: "Purchase Invoice"
			},
			{
				"label":frappe._("Budget Variance Report"),
				route: "query-report/Budget Variance Report",
				doctype: "Cost Center"
			},
			{
				"label":frappe._("Purchase Invoice Trends"),
				route: "query-report/Purchase Invoice Trends",
				doctype: "Purchase Invoice"
			},
			{
				"label":frappe._("Sales Invoice Trends"),
				route: "query-report/Sales Invoice Trends",
				doctype: "Sales Invoice"
			},
		]
	}
]

pscript['onload_accounts-home'] = function(wrapper) {
	frappe.views.moduleview.make(wrapper, "Accounts");
}