from __future__ import unicode_literals
import webnotes

items = [
	{
		"type": "Section",
		"title": "Organization",
		"icon": "icon-building"
	},
	{"doctype":"Company"}, 
	{"doctype":"Fiscal Year"}, 
	{"doctype":"Currency"}, 
	{
		"type": "Section",
		"title": "Users and Permissions",
		"icon": "icon-user"
	},
	{ 
		"doctype":"Profile",
	}, 
	{ 
		"doctype":"Role",
	}, 
	{ "title": "Permission Manager", 
		"route": "permission-manager", "type": "Link", "icon": "icon-shield" },
	{ "title": "User Properties", 
		"route": "user-properties", "type": "Link", "icon": "icon-user" },
	{
		"type": "Section",
		"title": "Master Data",
		"icon": "icon-star"
	},
	{
		"doctype": "Item",
		"dependencies": [
			{"doctype":"Item Group", "tree": "Sales Browser"}, 
			{"doctype":"Warehouse"}, 
			{"doctype":"UOM"}, 
			{"doctype":"Brand"},
			{"doctype":"Price List"}, 
			{ "title": "Stock Settings", 
				"route": "Form/Stock Settings", "type": "Link", "icon": "icon-cog" },
		],
	},
	{
		"doctype": "Customer",
		"dependencies": [
			{"doctype":"Customer Group", "tree": "Sales Browser"}, 
			{"doctype":"Territory", "tree": "Sales Browser"}, 
			{"doctype":"Sales Person", "tree": "Sales Browser"}, 
			{"doctype":"Contact"}, 
			{"doctype":"Address"}, 
			{ "title": "Selling Settings", 
				"route": "Form/Selling Settings", "type": "Link", "icon": "icon-cog" },
		]
	},
	{
		"doctype": "Supplier",
		"dependencies": [
			{"doctype":"Supplier Type"}, 
			{"doctype":"Contact"}, 
			{"doctype":"Address"}, 
			{ "title": "Buying Settings", 
				"route": "Form/Buying Settings", "type": "Link", "icon": "icon-cog" },
		]
	},
	{
		"type": "Section",
		"title": "Accounts",
		"icon": "icon-money"
	},
	{
		"doctype": "Account",
		"tree": "Accounts Browser",
		"dependencies": [
			{
				"title": "Bank Accounts",
				"doctype":"Account",
				"filter": {"account_type": "Bank or Cash"}
			}, 
			{
				"title": "Tax Accounts",
				"doctype":"Account",
				"filter": {"account_type": "Tax"}
			},
		]
	},
	{ 
		"doctype": "Cost Center",
		"tree": "Accounts Browser",
	},
	{ "doctype": "Sales Taxes and Charges Master" },
	{ "doctype": "Purchase Taxes and Charges Master" },
	{ "doctype": "Shipping Rule" },
	{ "doctype": "Currency Exchange" },
	{ "title": "Accounts Settings", 
		"route": "Form/Accounts Settings", "type": "Link", "icon": "icon-cog" },
	{
		"type": "Section",
		"title": "Opening Accounts and Stock",
		"icon": "icon-eye-open"
	},
	{ "doctype": "Stock Reconciliation" },
	{ 
		"doctype": "Journal Voucher",
		"title": "Opening Accounting Entries",
		"filter": {
			"is_opening": "Yes"
		}
	},
	{
		"type": "Section",
		"title": "Human Resource",
		"icon": "icon-group"
	},
	{ 
		"doctype": "Employee",
		"dependencies": [
			{ "doctype": "Employment Type" },
			{ "doctype": "Branch" },
			{ "doctype": "Department" },
			{ "doctype": "Designation" },
			{ "doctype": "Holiday List" },
			{ "doctype": "Grade" },
		]
	 },
	{ "doctype": "Salary Structure" },
	{ "doctype": "Leave Allocation" },
	{ "doctype": "Appraisal Template" },
	{
		"type": "Section",
		"title": "Printing",
		"icon": "icon-print"
	},
	{ "doctype": "Terms and Conditions" },
	{ "doctype": "Letter Head" },
	{ "doctype": "Print Heading" },
	{ "doctype": "Print Format", "filter": {"standard": "No"} },
	{
		"type": "Section",
		"title": "Email",
		"icon": "icon-envelope-alt"
	},
	{ 
		"title": "Outgoing Email Settings",
		"doctype": "Email Settings",
		"single": 1,
		"query": "select count(*) from tabSingles where doctype='Email Settings' and field='outgoing_mail_server'"
	},
	{ 
		"title": "Support Email Settings",
		"doctype": "Email Settings",
		"single": 1,
		"query": "select count(*) from tabSingles where doctype='Email Settings' and field='support_host'"
	},
	{ 
		"doctype": "Sales Email Settings",
		"single": 1,
		"query": "select count(*) from tabSingles where doctype='Sales Email Settings' and field='host'"
	},
	{ 
		"doctype": "Jobs Email Settings",
		"single": 1,
		"query": "select count(*) from tabSingles where doctype='Jobs Email Settings' and field='host'"
	},
	{ 
		"doctype": "Email Digest",
	},
	{
		"type": "Section",
		"title": "Customization",
		"icon": "icon-glass"
	},
	{ 
		"doctype": "Customize Form",
		"single": 1,
		"query": "select count(distinct doc_type) from `tabProperty Setter`"
	},
	{ "doctype": "Workflow" },
	{ "doctype": "Authorization Rule" },
	{ "doctype": "Custom Field" },
	{ "doctype": "Custom Script" },
	{
		"type": "Section",
		"title": "Tools",
		"icon": "icon-wrench"
	},
	{ "title": "Global Settings / Default Values", 
		"doctype": "Global Defaults", "single": 1,
	 	"query": """select count(*) from tabSingles where doctype='Global Defaults' 
		and field not in ('owner', 'creation', 'modified', 'modified_by')"""},
		
	{ "title": "Show / Hide Features", 
		"doctype": "Features Setup", "single": 1,
	 	"query": """select count(*) from tabSingles where doctype='Features Setup' 
		and field not in ('owner', 'creation', 'modified', 'modified_by')"""},

	{ "title": "Enable / Disable Email Notifications", 
		"doctype": "Notification Control", "single": 1,
	 	"query": """select count(*) from tabSingles where doctype='Notification Control' 
		and field in ('quotation', 'sales_order', 'sales_invoice', 'purchase_order', 'purchase_receipt', 'expense_claim', 'delivery_note')"""},

	{ "doctype": "File Data", "title": "Uploaded File Attachments" },
	{ 
		"doctype": "SMS Settings", 
		"single": 1,
	 	"query": "select count(*) from tabSingles where doctype='SMS Settings' and field='sms_gateway_url'"
	},

	{ "title": "Data Import", 
		"route": "data-import-tool", "type": "Link", "icon": "icon-upload" },
	{ "title": "Bulk Rename", 
		"route": "Form/Rename Tool", "type": "Link", "icon": "icon-upload" },
	{ "title": "Update Numbering Series", 
		"route": "Form/Naming Series", "type": "Link", "icon": "icon-sort-by-order" },
	{ "title": "Show / Hide Modules", 
		"route": "modules_setup", "type": "Link", "icon": "icon-th" },
	{ "title": "Send Bulk SMS to Leads / Contacts", 
		"route": "Form/SMS Center", "type": "Link", "icon": "icon-mobile-phone" },
	{
		"type": "Section",
		"title": "System Administration",
		"icon": "icon-cog"
	},
	{ "title": "Update ERPNext", 
		"route": "update-manager", "type": "Link", "icon": "icon-rss" },
	{ "title": "Manage 3rd Party Backups", 
		"route": "Form/Backup Manager", "type": "Link", "icon": "icon-cloud" },
	{ "title": "System Scheduler Errors", 
		"route": "Report/Scheduler Log", "type": "Link", "icon": "icon-exclamation-sign" },
]

@webnotes.whitelist(allow_roles=["System Manager"])
def get():
	for item in items:
		if item.get("type")=="Section":
			continue
		set_count(item)
		
		if item.get("dependencies"):
			for d in item["dependencies"]:
				set_count(d)
		
	return items
	
def set_count(item):
	if "query" in item:
		item["count"] = webnotes.conn.sql(item["query"])[0][0]
	elif "filter" in item:
		key = item["filter"].keys()[0]
		item["count"] = webnotes.conn.sql("""select count(*) from `tab%s` where
			%s = %s and docstatus < 2""" % (item["doctype"], key, "%s"),
			item["filter"][key])[0][0]
	elif "doctype" in item:
		item["count"] = webnotes.conn.sql("select count(*) from `tab%s` where docstatus<2" \
			% item["doctype"])[0][0]
