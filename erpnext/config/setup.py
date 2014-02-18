from frappe import _

data = [
	{
		"label": _("Customize"),
		"icon": "icon-glass",
		"items": [
			{
				"type": "doctype",
				"name": "Features Setup",
				"description": _("Show / Hide features like Serial Nos, POS etc.")
			},
			{
				"type": "doctype",
				"name": "Authorization Rule",
				"description": _("Create rules to restrict transactions based on values.")
			},
			{
				"type": "doctype",
				"name": "Notification Control",
				"label": _("Email Notifications"),
				"description": _("Automatically compose message on submission of transactions.")
			}
		]
	},
	{
		"label": _("Email"),
		"icon": "icon-envelope",
		"items": [
			{
				"type": "doctype",
				"name": "Email Digest",
				"description": _("Create and manage daily, weekly and monthly email digests.")
			},
			{
				"type": "doctype",
				"name": "Support Email Settings",
				"description": _("Setup incoming server for support email id. (e.g. support@example.com)")
			},
			{
				"type": "doctype",
				"name": "Sales Email Settings",
				"description": _("Setup incoming server for sales email id. (e.g. sales@example.com)")
			},
			{
				"type": "doctype",
				"name": "Jobs Email Settings",
				"description": _("Setup incoming server for jobs email id. (e.g. jobs@example.com)")
			},
		]
	},
	{
		"label": _("Masters"),
		"icon": "icon-star",
		"items": [
			{
				"type": "doctype",
				"name": "Company",
				"description": _("Company (not Customer or Supplier) master.")
			},
			{
				"type": "doctype",
				"name": "Item",
				"description": _("Item master.")
			},
			{
				"type": "doctype",
				"name": "Customer",
				"description": _("Customer master.")
			},
			{
				"type": "doctype",
				"name": "Supplier",
				"description": _("Supplier master.")
			},
			{
				"type": "doctype",
				"name": "Contact",
				"description": _("Contact master.")
			},
			{
				"type": "doctype",
				"name": "Address",
				"description": _("Address master.")
			},
		]
	},
	{
		"label": _("Accounts"),
		"icon": "icon-money",
		"items": [
			{
				"type": "page",
				"name": "Accounts Browser",
				"icon": "icon-sitemap",
				"label": _("Chart of Accounts"),
				"link": "Accounts Browser/Account",
				"description": _("Tree of finanial accounts.")
			},
			{
				"type": "page",
				"name": "Accounts Browser",
				"icon": "icon-sitemap",
				"label": _("Chart of Cost Centers"),
				"link": "Accounts Browser/Cost Center",
				"description": _("Tree of finanial Cost Centers.")
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
				"name": "Sales Taxes and Charges Master",
				"description": _("Tax template for selling transactions.")
			},
			{
				"type": "doctype",
				"name": "Purchase Taxes and Charges Master",
				"description": _("Tax template for buying transactions.")
			},
			{
				"type": "doctype",
				"name": "Currency",
				"description": _("Enable / disable currencies.")
			},
			{
				"type": "doctype",
				"name": "Shipping Rules",
				"description": _("Rules for adding shipping costs.")
			},
			{
				"type": "doctype",
				"name": "Currency Exchange",
				"description": _("Currency exchange rate master.")
			},
		]
	},
	{
		"label": _("Stock"),
		"icon": "icon-truck",
		"items": [
			{
				"type": "page",
				"name": "Sales Browser",
				"icon": "icon-sitemap",
				"label": _("Item Group Tree"),
				"link": "Sales Browser/Item Group",
				"description": _("Tree of Item Groups.")
			},
			{
				"type": "doctype",
				"name": "Stock Settings",
				"description": _("Default settings for stock transactions.")
			},
			{
				"type": "doctype",
				"name": "Warehouse",
				"description": _("Warehouses.")
			},
			{
				"type": "doctype",
				"name": "Brand",
				"description": _("Brand master.")
			},
			{
				"type": "doctype",
				"name": "Price List",
				"description": _("Price List master.")
			},
			{
				"type": "doctype",
				"name": "Stock Reconciliation",
				"description": _("Upload actual stock for a warehouse.")
			},
		]
	},
	{
		"label": _("Selling"),
		"icon": "icon-tag",
		"items": [
			{
				"type": "doctype",
				"name": "Selling Settings",
				"description": _("Default settings for selling transactions.")
			},
			{
				"type": "page",
				"label": _("Customer Group"),
				"name": "Sales Browser",
				"icon": "icon-sitemap",
				"link": "Sales Browser/Customer Group",
				"description": _("Manage Customer Group Tree.")
			},
			{
				"type": "page",
				"label": _("Territory"),
				"name": "Sales Browser",
				"icon": "icon-sitemap",
				"link": "Sales Browser/Territory",
				"description": _("Manage Territory Tree.")
			},
			{
				"type": "page",
				"label": _("Sales Person"),
				"name": "Sales Browser",
				"icon": "icon-sitemap",
				"link": "Sales Browser/Sales Person",
				"description": _("Manage Sales Person Tree.")
			},
		]
	},
	{
		"label": _("Buying"),
		"icon": "icon-shopping-cart",
		"items": [
			{
				"type": "doctype",
				"name": "Buying Settings",
				"description": _("Default settings for buying transactions.")
			},
			{
				"type": "doctype",
				"name": "Supplier Type",
				"description": _("Supplier Type master.")
			},
		]
	},
	{
		"label": _("Human Resources"),
		"icon": "icon-group",
		"items": [
			{
				"type": "doctype",
				"name": "Employee",
				"description": _("Employee master.")
			},
			{
				"type": "doctype",
				"name": "Employment Type",
				"description": _("Types of employment (permanent, contract, intern etc.).")
			},
			{
				"type": "doctype",
				"name": "Branch",
				"description": _("Organization branch master.")
			},
			{
				"type": "doctype",
				"name": "Department",
				"description": _("Organization unit (department) master.")
			},
			{
				"type": "doctype",
				"name": "Grade",
				"description": _("Employee grade.")
			},
			{
				"type": "doctype",
				"name": "Designation",
				"description": _("Employee designation (e.g. CEO, Director etc.).")
			},
			{
				"type": "doctype",
				"name": "Holiday List",
				"description": _("Holiday master.")
			},
			{
				"type": "doctype",
				"name": "Salary Structure",
				"description": _("Salary template master.")
			},
			{
				"type": "doctype",
				"name": "Appraisal Template",
				"description": _("Template for performance appraisals.")
			},
			{
				"type": "doctype",
				"name": "Leave Allocation",
				"description": _("Allocate leaves for a period.")
			},
		]
	},
]
