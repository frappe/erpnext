from __future__ import unicode_literals
from frappe import _
import frappe


def get_data():
	config = [
		{
			"label": _("Masters and Accounts"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
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
					"name": "Supplier",
					"description": _("Supplier database."),
					"onboard": 1,
				},
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
					"route": "Tree/Account",
					"description": _("Tree of financial accounts."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Journal Entry",
					"description": _("Accounting journal entries."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Opening Invoice Creation Tool",
					"description": _("Create Opening Sales and Purchase Invoices")
				},
			]
		},
		{
			"label": _("Billing"),
			"items": [
				{
					"type": "doctype",
					"name": "Sales Invoice",
					"description": _("Bills raised to Customers."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Purchase Invoice",
					"description": _("Bills raised by Suppliers."),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Payment Request",
					"description": _("Payment Request"),
				},
				{
					"type": "doctype",
					"name": "Payment Entry",
					"description": _("Bank/Cash transactions against party or for internal transfer")
				},

				# Reports
				{
					"type": "report",
					"name": "Ordered Items To Be Billed",
					"is_query_report": True,
					"reference_doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"name": "Delivered Items To Be Billed",
					"is_query_report": True,
					"reference_doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"name": "Purchase Order Items To Be Billed",
					"is_query_report": True,
					"reference_doctype": "Purchase Invoice"
				},
				{
					"type": "report",
					"name": "Received Items To Be Billed",
					"is_query_report": True,
					"reference_doctype": "Purchase Invoice"
				},
			]

		},
		{
			"label": _("Setup"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Opening Invoice Creation Tool",
					"description": _("Create Opening Sales and Purchase Invoices")
				},
				{
					"type": "doctype",
					"name": "Accounts Settings",
					"description": _("Default settings for accounting transactions.")
				},
				{
					"type": "doctype",
					"name": "Fiscal Year",
					"description": _("Financial / accounting year.")
				},
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
				{
					"type": "doctype",
					"name": "Auto Repeat",
					"label": _("Auto Repeat"),
					"description": _("To make recurring documents")
				},
				{
					"type": "doctype",
					"name": "C-Form",
					"description": _("C-Form records"),
					"country": "India"
				}
			]
		},
		{
			"label": _("Financial Statements"),
			"items": [
				{
					"type": "report",
					"name": "General Ledger",
					"doctype": "GL Entry",
					"is_query_report": True,
					"onboard": 1,
				},
				{
					"type": "report",
					"name": "Accounts Receivable",
					"doctype": "Sales Invoice",
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
					"name": "Trial Balance",
					"doctype": "GL Entry",
					"is_query_report": True,
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
				{
					"type": "report",
					"name": "Profit and Loss Statement",
					"doctype": "GL Entry",
					"is_query_report": True
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
			"label": _("Banking and Payments"),
			"items": [
				{
					"type": "doctype",
					"label": _("Update Bank Transaction Dates"),
					"name": "Bank Reconciliation",
					"description": _("Update bank payment dates with journals.")
				},
				{
					"type": "doctype",
					"label": _("Match Payments with Invoices"),
					"name": "Payment Reconciliation",
					"description": _("Match non-linked Invoices and Payments.")
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
					"name": "Bank Guarantee",
					"doctype": "Bank Guarantee"
				},
			]
		},
		{
			"label": _("Taxes"),
			"items": [
				{
					"type": "doctype",
					"name": "Tax Category",
					"description": _("Tax Category for overriding tax rates.")
				},
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
					"route": "Tree/Cost Center",
					"description": _("Tree of financial Cost Centers."),
				},
				{
					"type": "doctype",
					"name": "Budget",
					"description": _("Define budget for a financial year.")
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
				{
					"type": "doctype",
					"name": "Period Closing Voucher",
					"description": _("Close Balance Sheet and book Profit or Loss.")
				},
				{
					"type": "doctype",
					"name": "Cheque Print Template",
					"description": _("Setup cheque dimensions for printing")
				},
			]
		},
		{
			"label": _("Key Reports"),
			"items": [
				{
					"type": "report",
					"name": "Gross Profit",
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
					"name": "Purchase Register",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Purchase Invoice Trends",
					"is_query_report": True,
					"doctype": "Purchase Invoice"
				},
				{
					"type": "report",
					"name": "Sales Invoice Trends",
					"is_query_report": True,
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"name": "Item-wise Sales Register",
					"is_query_report": True,
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"name": "Item-wise Purchase Register",
					"is_query_report": True,
					"doctype": "Purchase Invoice"
				},
				{
					"type": "report",
					"name": "Profitability Analysis",
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
			"label": _("Other Reports"),
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
					"name": "Accounts Receivable Summary",
					"doctype": "Sales Invoice",
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
				}
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
		{
			"label": _("Help"),
			"icon": "fa fa-facetime-video",
			"items": [
				{
					"type": "help",
					"label": _("Chart of Accounts"),
					"youtube_id": "DyR-DST-PyA"
				},
				{
					"type": "help",
					"label": _("Opening Accounting Balance"),
					"youtube_id": "kdgM20Q-q68"
				},
				{
					"type": "help",
					"label": _("Setting up Taxes"),
					"youtube_id": "nQ1zZdPgdaQ"
				}
			]
		}
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
		]
	}

	subscriptions = {
		"label": _("Subscription Management"),
		"icon": "fa fa-microchip ",
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
	}


	countries = frappe.get_all("Company", fields="country")
	countries = [country["country"] for country in countries]
	if "India" in countries:
		config.insert(7, gst)
	domains = frappe.get_active_domains()
	if "Services" in domains:
		config.insert(5, subscriptions)
	else:
		config.insert(7, subscriptions)
	return config
