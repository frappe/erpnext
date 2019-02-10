# coding=utf-8

from __future__ import unicode_literals
from frappe import _

def get_data():
	colors = {
		"Stock": "#f39c12",
		"Selling": "#1abc9c",
		"Buying": "#c0392b",
		"HR": "#2ecc71",
		"Projects": "#8e44ad",
		"Support": "#2c3e50",
		"Accounts": "#3498db",
		"Tools": "#FFF5A7"
	}

	return [
		{"module_name": "Item", "_doctype": "Item", "type": "list",
			"color": colors["Stock"], "icon": "octicon octicon-package"},
		{"module_name": "Item Price", "_doctype": "Item Price", "type": "list",
			"color": colors["Stock"], "icon": "fa fa-usd"},
		{"module_name": "Pricing Rule", "_doctype": "Pricing Rule", "type": "list",
			"color": colors["Stock"], "icon": "fa fa-usd"},

		{"module_name": "Customer", "_doctype": "Customer", "type": "list",
			"color": colors["Selling"], "icon": "octicon octicon-tag"},
		{"module_name": "Supplier", "_doctype": "Supplier", "type": "list",
			"color": colors["Buying"], "icon": "octicon octicon-briefcase"},
		{"module_name": "Letter of Credit", "_doctype": "Letter of Credit", "type": "list",
			"color": colors["Buying"], "icon": "fa fa-university"},
		{"module_name": "Employee", "_doctype": "Employee", "type": "list",
			"color": colors["HR"], "icon": "octicon octicon-organization"},
		{"module_name": "Account", "_doctype": "Account", "type": "link", "link": "Tree/Account", "label": _("Chart of Accounts"),
			"color": colors["Accounts"], "icon": "fa fa-sitemap"},

		{"module_name": "Territory", "_doctype": "Territory", "type": "link", "link": "Tree/Territory",
			"color": colors["Selling"], "icon": "fa fa-flag"},
		{"module_name": "Sales Person", "_doctype": "Sales Person", "type": "link", "link": "Tree/Sales Person",
			"color": colors["Selling"], "icon": "fa fa-male"},

		{"module_name": "Issue", "_doctype": "Issue", "type": "list",
			"color": colors["Support"], "icon": "octicon octicon-issue-opened"},
		{"module_name": "ToDo", "_doctype": "ToDo", "type": "list",
			"color": colors["Tools"], "icon": "fa fa-check", "reverse": 1},

		{"module_name": "Project", "_doctype": "Project", "type": "list",
			"color": colors["Projects"], "icon": "octicon octicon-rocket"},
		{"module_name": "Task", "_doctype": "Task", "type": "list",
			"color": colors["Projects"], "icon": "octicon octicon-rocket"},

		{"module_name": "Sales Order", "_doctype": "Sales Order", "type": "list",
			"color": colors["Selling"], "icon": "fa fa-file-text"},
		{"module_name": "Purchase Order", "_doctype": "Purchase Order", "type": "list",
			"color": colors["Buying"], "icon": "fa fa-file-text"},
		{"module_name": "Delivery Note", "_doctype": "Delivery Note", "type": "list",
			"color": colors["Stock"], "icon": "fa fa-truck"},
		{"module_name": "Purchase Receipt", "_doctype": "Purchase Receipt", "type": "list",
			"color": colors["Stock"], "icon": "fa fa-truck"},
		{"module_name": "Landed Cost Voucher", "_doctype": "Landed Cost Voucher", "type": "list",
			"color": colors["Stock"], "icon": "fa fa-plane"},
		{"module_name": "Sales Invoice", "_doctype": "Sales Invoice", "type": "list",
			"color": colors["Accounts"], "icon": "fa fa-file-text"},
		{"module_name": "Purchase Invoice", "_doctype": "Purchase Invoice", "type": "list",
			"color": colors["Accounts"], "icon": "fa fa-file-text"},

		{"module_name": "Stock Entry", "_doctype": "Stock Entry", "type": "list",
			"color": colors["Stock"], "icon": "fa fa-truck"},
		{"module_name": "Stock Reconciliation", "_doctype": "Stock Reconciliation", "type": "list",
			"color": colors["Stock"], "icon": "fa fa-files-o"},

		{"module_name": "Journal Entry", "_doctype": "Journal Entry", "type": "list",
			"color": colors["Accounts"], "icon": "fa fa-book"},
		{"module_name": "Payment Entry", "_doctype": "Payment Entry", "type": "list",
			"color": colors["Accounts"], "icon": "fa fa-money"},
		{"module_name": "Payment Reconciliation", "_doctype": "Payment Reconciliation", "type": "list",
			"color": colors["Accounts"], "icon": "fa fa-files-o"},

		{"module_name": "Leaderboard", "type": "page", "link": "leaderboard", "label": _("Leaderboard"),
			"color": "#589494", "icon": "octicon octicon-graph"},

		{"module_name": "General Ledger", "_report": "General Ledger", "type": "query-report", "link": "query-report/General Ledger",
			"color": colors["Accounts"], "icon": "fa fa-book"},
		{"module_name": "Accounts Receivable", "_report": "Accounts Receivable", "type": "query-report", "link": "query-report/Accounts Receivable",
			"color": colors["Selling"], "icon": "fa fa-tasks"},
		{"module_name": "Accounts Payable", "_report": "Accounts Payable", "type": "query-report", "link": "query-report/Accounts Payable",
			"color": colors["Buying"], "icon": "fa fa-tasks"},
		{"module_name": "Customer Ledger Summary", "_report": "Customer Ledger Summary", "type": "query-report", "link": "query-report/Customer Ledger Summary",
			"color": colors["Selling"], "icon": "fa fa-book"},
		{"module_name": "Supplier Ledger Summary", "_report": "Supplier Ledger Summary", "type": "query-report", "link": "query-report/Supplier Ledger Summary",
			"color": colors["Buying"], "icon": "fa fa-book"},
		{"module_name": "Customer Credit Balance", "_report": "Customer Credit Balance", "type": "query-report", "link": "query-report/Customer Credit Balance",
			"color": colors["Selling"], "icon": "fa fa-credit-card"},

		{"module_name": "Sales Analytics", "_report": "Sales Analytics", "type": "query-report", "link": "query-report/Sales Analytics",
			"color": colors["Selling"], "icon": "fa fa-line-chart"},
		{"module_name": "Purchase Analytics", "_report": "Purchase Analytics", "type": "query-report", "link": "query-report/Purchase Analytics",
			"color": colors["Buying"], "icon": "fa fa-line-chart"},

		{"module_name": "Stock Ledger", "_report": "Stock Ledger", "type": "query-report", "link": "query-report/Stock Ledger",
			"color": colors["Stock"], "icon": "fa fa-exchange"},
		{"module_name": "Stock Balance", "_report": "Stock Balance", "type": "query-report", "link": "query-report/Stock Balance",
			"color": colors["Stock"], "icon": "octicon octicon-package"},

		{"module_name": "Gross Profit", "_report": "Gross Profit", "type": "query-report", "link": "query-report/Gross Profit",
			"color": colors["Accounts"], "icon": "fa fa-usd"},
		{"module_name": "Profit and Loss Statement", "_report": "Profit and Loss Statement", "type": "query-report", "link": "query-report/Profit and Loss Statement",
			"color": colors["Accounts"], "icon": "fa fa-bar-chart"},
		{"module_name": "Balance Sheet", "_report": "Balance Sheet", "type": "query-report", "link": "query-report/Balance Sheet",
			"color": colors["Accounts"], "icon": "fa fa-bar-chart"},
		{"module_name": "Trial Balance", "_report": "Trial Balance", "type": "query-report", "link": "query-report/Trial Balance",
			"color": colors["Accounts"], "icon": "fa fa-balance-scale"},
		{"module_name": "Trial Balance for Party", "_report": "Trial Balance for Party", "type": "query-report", "link": "query-report/Trial Balance for Party",
			"color": colors["Accounts"], "icon": "fa fa-balance-scale"},
		{"module_name": "Trial Balance (Simple)", "_report": "Trial Balance (Simple)", "type": "query-report", "link": "query-report/Trial Balance (Simple)",
			"color": colors["Accounts"], "icon": "fa fa-exchange"},
		{"module_name": "Sales Payment Summary", "_report": "Sales Payment Summary", "type": "query-report", "link": "query-report/Sales Payment Summary",
			"color": colors["Accounts"], "icon": "fa fa-exchange"},
	]
