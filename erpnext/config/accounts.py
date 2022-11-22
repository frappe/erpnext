from __future__ import unicode_literals
from frappe import _
import frappe


def get_data():
	config = [
		{
			"label": _("Accounts Receivable"),
			"items": [
				{
					"type": "doctype",
					"name": "Sales Invoice",
					"description": _("Bills raised to Customers."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Account Statement Payment",
					"description": _("Bills raised to Patient Statement."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Reason for sale",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Customer",
					"description": _("Customer database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Debit Note CXC",
					"description": _("Debit Note Database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Credit Note CXC",
					"description": _("Credit Note Database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Return credit notes",
					"description": _("Return credit notes."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Cancellation Of Invoices",
					"description": _("Cancellation Of Invoices"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Customer Documents",
					"description": _("Customer Documents"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Customer Retention",
					"description": _("Customer Retention Database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Payment Entry",
					"description": _("Bank/Cash transactions against party or for internal transfer")
				},
				{
					"type": "doctype",
					"name": "Apply Payment Entries Without References",
					"description": _("Assignment payment entries without references.")
				},
				{
					"type": "doctype",
					"name": "Payment Request",
					"description": _("Payment Request"),
				},
				{
					"type": "report",
					"name": "Cancellation Of Invoices",
					"doctype": "Cancellation Of Invoices",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Advances Applied Customer",
					"doctype": "Payment Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Payment Entry CXC",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Receivable",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Receivable Summary",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Sales Register",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Item-wise Sales Register",
					"is_query_report": True,
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"name": "Ordered Items To Be Billed",
					"is_query_report": True,
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"name": "Delivered Items To Be Billed",
					"is_query_report": True,
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"name": "Customer Documents",
					"doctype": "Customer Documents",
					"is_query_report": True
				},
			]
		},
		{
			"label": _("Accounts Payable"),
			"items": [
				{
					"type": "doctype",
					"name": "Purchase Invoice",
					"description": _("Bills raised by Suppliers."),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Supplier",
					"description": _("Supplier database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Debit Note CXP",
					"description": _("Debit Note Database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Credit Note CXP",
					"description": _("Credit Note Database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Supplier Documents",
					"description": _("Supplier Documents"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Supplier Retention",
					"description": _("Supplier Retention Database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Cancellation Of Supplier Retentions",
					"description": _("Cancellation Of Supplier Retentions"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Payment Entry",
					"description": _("Bank/Cash transactions against party or for internal transfer")
				},
				{
					"type": "report",
					"name": "Advances Applied Supplier",
					"doctype": "Payment Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Payment Entry CXP",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Payable",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Supplier Retention",
					"doctype": "Supplier Retention",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Payable Summary",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Purchase Register",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Item-wise Purchase Register",
					"is_query_report": True,
					"doctype": "Purchase Invoice"
				},
				{
					"type": "report",
					"name": "Purchase Order Items To Be Billed",
					"is_query_report": True,
					"doctype": "Purchase Invoice"
				},
				{
					"type": "report",
					"name": "Received Items To Be Billed",
					"is_query_report": True,
					"doctype": "Purchase Invoice"
				},
				{
					"type": "report",
					"name": "Provider Withholding Vouchers",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Suplier Documents",
					"doctype": "Supplier Documents",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Payment Entry",
					"doctype": "Payment Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Unallocated Payment Entry",
					"doctype": "Payment Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Payment Entry Applied",
					"doctype": "Payment Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Payable Analisis",
					"doctype": "Supplier",
					"is_query_report": True,
				},
			]
		},
		{
			"label": _("Accounting Masters"),
			"items": [
				{
					"type": "doctype",
					"name": "Company",
					"description": _("Company (not Customer or Supplier) master."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Account",
					"icon": "fa fa-sitemap",
					"label": _("Chart of Accounts"),
					"route": "#Tree/Account",
					"description": _("Tree of financial accounts."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Accounts Settings",
				},
				{
					"type": "doctype",
					"name": "Fiscal Year",
					"description": _("Financial / accounting year.")
				},
				{
					"type": "doctype",
					"name": "Accounting Dimension",
				},
				{
					"type": "doctype",
					"name": "Finance Book",
				},
				{
					"type": "doctype",
					"name": "Accounting Period",
				},
				{
					"type": "doctype",
					"name": "Payment Term",
					"description": _("Payment Terms based on conditions")
				},
			]
		},
		{
			"label": _("Bank Statement"),
			"items": [
				{
					"type": "doctype",
					"label": _("Bank"),
					"name": "Bank",
				},
				{
					"type": "doctype",
					"label": _("Account Levels"),
					"name": "Account Levels",
				},
				{
					"type": "doctype",
					"label": _("Bank Account"),
					"name": "Bank Account",
				},
				{
					"type": "doctype",
					"name": "Bank Statement Transaction Entry",
				},
				{
					"type": "doctype",
					"label": _("Bank Statement Settings"),
					"name": "Bank Statement Settings",
				},
			]
		},
		{
			"label": _("Banking and Payments"),
			"items": [
				{
					"type": "doctype",
					"label": _("Match Payments with Invoices"),
					"name": "Payment Reconciliation",
					"description": _("Match non-linked Invoices and Payments.")
				},
				{
					"type": "doctype",
					"label": _("Update Bank Transaction Dates"),
					"name": "Bank Reconciliation",
					"description": _("Update bank payment dates with journals.")
				},
				{
					"type": "doctype",
					"label": _("Invoice Discounting"),
					"name": "Invoice Discounting",
				},
				{
					"type": "report",
					"name": "Bank Reconciliation Statement",
					"is_query_report": True,
					"doctype": "Journal Entry"
				},
				{
					"type": "report",
					"name": "Bank Clearance Summary",
					"is_query_report": True,
					"doctype": "Journal Entry"
				},
				{
					"type": "doctype",
					"name": "Bank Guarantee"
				},
				{
					"type": "doctype",
					"name": "Cheque Print Template",
					"description": _("Setup cheque dimensions for printing")
				},
			]
		},
		{
			"label": _("Bank Transactions"),
			"items": [
				{
              		"type": "doctype",
              		"name": "Bank Transactions",
              		"label": _("Bank Transactions"),
              		"description": _("This option is for create new bank transactions."),
            	},
            	{
              		"type": "doctype",
              		"name": "Bank reconciliations",
              		"label": _("Bank reconciliations"),
              		"description": _("Create Bank reconciliations"),
            	},
				{
					"type": "doctype",
					"label": _("Bank Book Reconciliations"),
					"name": "Bank Book Reconciliations",
					"description": _("Bank Book Reconciliations")
				},
				{
              		"type": "doctype",
              		"name": "Cancel Bank Checks",
              		"label": _("Cancel Bank Checks"),
              		"description": _("This option is for create new Cancel Bank Checks."),
            	},
				{
              		"type": "doctype",
              		"name": "Correlative Of Bank Checks",
              		"label": _("Correlative Of Bank Checks"),
              		"description": _("This option is for create new Correlative Of Bank Checks."),
            	},
            	{
              		"type": "doctype",
              		"name": "Reconciled balances",
              		"label": _("Reconciled balances"),
              		"description": _("Create Reconciled balances"),
            	},
				{
              		"type": "doctype",
              		"name": "Voided Check",
              		"label": _("Voided Check"),
              		"description": _("Create Voided Check"),
            	},
				{
					"type": "report",
					"name": "Credit Note Transaction",
					"doctype": "Bank Transactions",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Debit Note Transaction",
					"doctype": "Bank Transactions",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Bank Check Of Bank Transactions",
					"doctype": "Bank Transactions",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Bank Deposit",
					"doctype": "Bank Transactions",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Bank Book",
					"doctype": "Bank Transactions",
					"is_query_report": True,
				},
				{
              		"type": "doctype",
              		"name": "Print Bank Check",
              		"label": _("Print Bank Check"),
              		"description": _("Create Print Bank Check"),
            	},
				
			]
		},
		{
			"label": _("General Ledger"),
			"items": [
				{
					"type": "doctype",
					"name": "Journal Entry",
					"description": _("Accounting journal entries.")
				},
				{
					"type": "report",
					"name": "General Ledger",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Customer Ledger Summary",
					"doctype": "Sales Invoice",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Supplier Ledger Summary",
					"doctype": "Sales Invoice",
					"is_query_report": True,
				}
			]
		},
		{
			"label": _("Taxes"),
			"items": [
				{
					"type": "doctype",
					"name": "Sales Taxes and Charges Template",
					"description": _("Tax template for selling transactions.")
				},
				{
					"type": "doctype",
					"name": "Purchase Taxes and Charges Template",
					"description": _("Tax template for buying transactions.")
				},
				{
					"type": "doctype",
					"name": "Item Tax Template",
					"description": _("Tax template for item tax rates.")
				},
				{
					"type": "doctype",
					"name": "Tax Category",
					"description": _("Tax Category for overriding tax rates.")
				},
				{
					"type": "doctype",
					"name": "Tax Rule",
					"description": _("Tax Rule for transactions.")
				},
				{
					"type": "doctype",
					"name": "Tax Withholding Category",
					"description": _("Tax Withholding rates to be applied on transactions.")
				},
			]
		},
		{
			"label": _("Cost Center and Budgeting"),
			"items": [
				{
					"type": "doctype",
					"name": "Cost Center",
					"icon": "fa fa-sitemap",
					"label": _("Chart of Cost Centers"),
					"route": "#Tree/Cost Center",
					"description": _("Tree of financial Cost Centers."),
				},
				{
					"type": "doctype",
					"name": "Budget",
					"description": _("Define budget for a financial year.")
				},
				{
					"type": "doctype",
					"name": "Accounting Dimension",
				},
				{
					"type": "report",
					"name": "Budget Variance Report",
					"is_query_report": True,
					"doctype": "Cost Center"
				},
				{
					"type": "doctype",
					"name": "Monthly Distribution",
					"description": _("Seasonality for setting budgets, targets etc.")
				},
			]
		},
		{
			"label": _("Financial Statements"),
			"items": [
				{
					"type": "report",
					"name": "Trial Balance",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Daily Books",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Analytical Ledger",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Profit and Loss Statement",
					"doctype": "GL Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Balance Sheet",
					"doctype": "GL Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Cash Flow",
					"doctype": "GL Entry",
					"is_query_report": True
				},
			]
		},
		{
			"label": _("Opening and Closing"),
			"items": [
				{
					"type": "doctype",
					"name": "Opening Invoice Creation Tool",
				},
				{
					"type": "doctype",
					"name": "Chart of Accounts Importer",
				},
				{
					"type": "doctype",
					"name": "Period Closing Voucher",
					"description": _("Close Balance Sheet and book Profit or Loss.")
				},
			]

		},
		{
			"label": _("Multi Currency"),
			"items": [
				{
					"type": "doctype",
					"name": "Currency",
					"description": _("Enable / disable currencies.")
				},
				{
					"type": "doctype",
					"name": "Currency Exchange",
					"description": _("Currency exchange rate master.")
				},
				{
					"type": "doctype",
					"name": "Exchange Rate Revaluation",
					"description": _("Exchange Rate Revaluation master.")
				},
			]
		},
		{
			"label": _("Settings"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Payment Gateway Account",
					"description": _("Setup Gateway accounts.")
				},
				{
					"type": "doctype",
					"name": "Terms and Conditions",
					"label": _("Terms and Conditions Template"),
					"description": _("Template of terms or contract.")
				},
				{
					"type": "doctype",
					"name": "Mode of Payment",
					"description": _("e.g. Bank, Cash, Credit Card")
				},
			]
		},
		{
			"label": _("Subscription Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Subscriber",
				},
				{
					"type": "doctype",
					"name": "Subscription Plan",
				},
				{
					"type": "doctype",
					"name": "Subscription"
				},
				{
					"type": "doctype",
					"name": "Subscription Settings"
				}
			]
		},
		{
			"label": _("Profitability"),
			"items": [
				{
					"type": "report",
					"name": "Gross Profit",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Profitability Analysis",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Sales Invoice Trends",
					"is_query_report": True,
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"name": "Purchase Invoice Trends",
					"is_query_report": True,
					"doctype": "Purchase Invoice"
				},
			]
		},
		{
			"label": _("Reports"),
			"icon": "fa fa-table",
			"items": [
				{
					"type": "report",
					"name": "Trial Balance for Party",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Payment Period Based On Invoice Date",
					"is_query_report": True,
					"doctype": "Journal Entry"
				},
				{
					"type": "report",
					"name": "Sales Partners Commission",
					"is_query_report": True,
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Customer Credit Balance",
					"doctype": "Customer"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Sales Payment Summary",
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Address And Contacts",
					"doctype": "Address"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Discount Per Invoice",
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Advances Applied",
					"doctype": "Payment Entry"
				},
				{
					"type": "doctype",
					"name": "Cash Report",
				},

				{
					"type": "report",
					"name": "Balance Sheet Accounts",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Statement Of Income",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Provider Account Statement",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Ledger",
					"doctype": "GL Entry",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Consolidated Financial Statement",
					"doctype": "GL Entry",
					"is_query_report": True
				},
			]
		},
		{
			"label": _("Share Management"),
			"icon": "fa fa-microchip ",
			"items": [
				{
					"type": "doctype",
					"name": "Shareholder",
					"description": _("List of available Shareholders with folio numbers")
				},
				{
					"type": "doctype",
					"name": "Share Transfer",
					"description": _("List of all share transactions"),
				},
				{
					"type": "report",
					"name": "Share Ledger",
					"doctype": "Share Transfer",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Share Balance",
					"doctype": "Share Transfer",
					"is_query_report": True
				}
			]
		},

	]

	gst = {
		"label": _("Goods and Services Tax (GST India)"),
		"items": [
			{
				"type": "doctype",
				"name": "GST Settings",
			},
			{
				"type": "doctype",
				"name": "GST HSN Code",
			},
			{
				"type": "report",
				"name": "GSTR-1",
				"is_query_report": True
			},
			{
				"type": "report",
				"name": "GSTR-2",
				"is_query_report": True
			},
			{
				"type": "doctype",
				"name": "GSTR 3B Report",
			},
			{
				"type": "report",
				"name": "GST Sales Register",
				"is_query_report": True
			},
			{
				"type": "report",
				"name": "GST Purchase Register",
				"is_query_report": True
			},
			{
				"type": "report",
				"name": "GST Itemised Sales Register",
				"is_query_report": True
			},
			{
				"type": "report",
				"name": "GST Itemised Purchase Register",
				"is_query_report": True
			},
			{
				"type": "doctype",
				"name": "C-Form",
				"description": _("C-Form records"),
				"country": "India"
			},
		]
	}


	countries = frappe.get_all("Company", fields="country")
	countries = [country["country"] for country in countries]
	if "India" in countries:
		config.insert(9, gst)
	domains = frappe.get_active_domains()
	return config
